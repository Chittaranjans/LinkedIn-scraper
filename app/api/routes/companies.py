from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query
from typing import Optional, List
from uuid import uuid4
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel, HttpUrl

from app.core.security import verify_api_key
from app.db.mongodb import get_companies_collection, get_tasks_collection
from app.scrapers.company_scraper import CompanyScraper
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class CompanyRequest(BaseModel):
    url: HttpUrl
    include_employees: bool = True
    background: bool = True

async def create_task(task_type: str, url: HttpUrl) -> str:
    """Create a task record in the database"""
    task_id = str(uuid4())
    task = {
        "_id": task_id,
        "type": task_type,
        "url": str(url),  # Convert HttpUrl to string
        "status": "pending",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    tasks_collection = get_tasks_collection()
    await tasks_collection.insert_one(task)
    return task_id

@router.post("/scrape")
async def scrape_company(
    request: CompanyRequest,
    background_tasks: BackgroundTasks
):
    # Create task record first
    task_id = await create_task("company_scrape", request.url)
    
    # Add debug log
    logger.info(f"Created task {task_id} for URL {request.url}")
    
    # Start background task with proper error handling
    async def scrape_with_error_handling(url, task_id):
        try:
            logger.info(f"Starting background task {task_id} for {url}")
            
            # Update task to "in_progress" immediately
            tasks_collection = get_tasks_collection()
            await tasks_collection.update_one(
                {"_id": task_id},
                {"$set": {"status": "in_progress", "updated_at": datetime.now()}}
            )
            
            # Create scraper and run
            scraper = CompanyScraper()
            result = await scraper.scrape_company(str(url), task_id, include_employees=True)
            
            logger.info(f"Background task {task_id} completed: {result is not None}")
        except Exception as e:
            logger.error(f"Unhandled exception in background task {task_id}: {str(e)}")
            # Update task as failed
            tasks_collection = get_tasks_collection()
            await tasks_collection.update_one(
                {"_id": task_id},
                {"$set": {"status": "failed", "error": str(e), "updated_at": datetime.now()}}
            )
    
    # Use add_task to run the function in the background
    background_tasks.add_task(scrape_with_error_handling, request.url, task_id)
    
    return {"task_id": str(task_id)}

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a scraping task"""
    tasks_collection = get_tasks_collection()
    task = await tasks_collection.find_one({"_id": task_id})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return {
        "task_id": task_id,
        "status": task.get("status", "unknown"),
        "updated_at": task.get("updated_at", None),
        "result_id": str(task.get("result_id", "")) if task.get("result_id") else None,
        "error": task.get("error", None)
    }

@router.get("/")
async def list_all_companies(
    limit: int = Query(50, le=500),
    skip: int = Query(0, ge=0),
    api_key: str = Depends(verify_api_key)
):
    """Get all companies in the database with pagination"""
    collection = get_companies_collection()
    
    # Execute query with pagination
    cursor = collection.find().sort("metadata.scraped_at", -1).skip(skip).limit(limit)
    companies = await cursor.to_list(length=limit)
    
    # Get total count for pagination info
    total = await collection.count_documents({})
    
    # Convert MongoDB _id to string
    for company in companies:
        company["_id"] = str(company["_id"])
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": companies
    }

@router.get("/search")
async def search_companies(
    q: Optional[str] = None,
    name: Optional[str] = None,
    industry: Optional[str] = None,
    company_size: Optional[str] = None,
    website: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = Query(10, le=100),
    skip: int = Query(0, ge=0),
    api_key: str = Depends(verify_api_key)
):
    """Search for companies in the database with flexible parameters"""
    collection = get_companies_collection()
    
    # Build query
    query = {}
    if q:
        # Full text search across all fields
        query["$text"] = {"$search": q}
    
    # Add specific field searches
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if industry:
        query["industry"] = {"$regex": industry, "$options": "i"}
    if company_size:
        query["company_size"] = {"$regex": company_size, "$options": "i"}
    if website:
        query["website"] = {"$regex": website, "$options": "i"}
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    
    # Execute query
    cursor = collection.find(query).skip(skip).limit(limit)
    companies = await cursor.to_list(length=limit)
    
    # Convert MongoDB _id to string
    for company in companies:
        company["_id"] = str(company["_id"])
        
    return companies

@router.get("/{company_id}")
async def get_company(
    company_id: str = Path(..., description="Company ID in the database"),
    api_key: str = Depends(verify_api_key)
):
    """Get a specific company by ID"""
    collection = get_companies_collection()
    
    try:
        company = await collection.find_one({"_id": ObjectId(company_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid company ID format")
        
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    company["_id"] = str(company["_id"])
    return company
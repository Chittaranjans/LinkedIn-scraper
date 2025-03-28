from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query
from typing import Optional, List
from uuid import uuid4
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel, HttpUrl

from app.core.security import verify_api_key
from app.db.mongodb import get_jobs_collection, get_tasks_collection
from app.scrapers.job_scraper import JobScraper

router = APIRouter()

class JobSearchRequest(BaseModel):
    keywords: str
    location: Optional[str] = None
    limit: int = 20
    background: bool = True

class JobURLRequest(BaseModel):
    url: HttpUrl
    background: bool = True

@router.post("/search")
async def search_jobs_on_linkedin(
    request: JobSearchRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Search and scrape jobs from LinkedIn with proxy rotation"""
    # Create task in database first
    task_id = str(uuid4())
    task = {
        "_id": task_id,
        "type": "job_search_scrape",
        "keywords": request.keywords,
        "location": request.location,
        "limit": request.limit,
        "status": "pending",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    tasks_collection = get_tasks_collection()
    await tasks_collection.insert_one(task)
    
    # Handle background vs. synchronous processing
    if request.background:
        # Start background scraping task
        scraper = JobScraper()
        background_tasks.add_task(
            scraper.search_jobs, 
            request.keywords,
            request.location,
            request.limit,
            task_id
        )
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Job search started in background"
        }
    else:
        # Run synchronously (not recommended for production)
        scraper = JobScraper()
        result = await scraper.search_jobs(
            request.keywords,
            request.location,
            request.limit,
            task_id
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to search jobs")
            
        return {
            "task_id": task_id,
            "status": "completed",
            "data": result
        }

@router.post("/scrape")
async def scrape_job(
    request: JobURLRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Scrape a specific LinkedIn job with proxy rotation"""
    # Create task in database first
    task_id = str(uuid4())
    task = {
        "_id": task_id,
        "type": "job_scrape",
        "url": str(request.url),
        "status": "pending",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    tasks_collection = get_tasks_collection()
    await tasks_collection.insert_one(task)
    
    # Handle background vs. synchronous processing
    if request.background:
        # Start background scraping task
        scraper = JobScraper()
        background_tasks.add_task(
            scraper.scrape_job, 
            str(request.url), 
            task_id
        )
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Scraping started in background"
        }
    else:
        # Run synchronously (not recommended for production)
        scraper = JobScraper()
        result = await scraper.scrape_job(
            str(request.url), 
            task_id
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to scrape job")
            
        return {
            "task_id": task_id,
            "status": "completed",
            "data": result
        }

@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str = Path(..., description="Task ID of the scraping job"),
    api_key: str = Depends(verify_api_key)
):
    """Get status of a scraping task"""
    # Implementation same as other routes

@router.get("/")
async def list_all_jobs(
    limit: int = Query(50, le=500),
    skip: int = Query(0, ge=0),
    api_key: str = Depends(verify_api_key)
):
    """Get all jobs in the database with pagination"""
    collection = get_jobs_collection()
    
    # Execute query with pagination
    cursor = collection.find().sort("metadata.scraped_at", -1).skip(skip).limit(limit)
    jobs = await cursor.to_list(length=limit)
    
    # Get total count for pagination info
    total = await collection.count_documents({})
    
    # Convert MongoDB _id to string
    for job in jobs:
        job["_id"] = str(job["_id"])
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": jobs
    }

@router.get("/search")
async def search_jobs_in_database(
    q: Optional[str] = None,
    title: Optional[str] = None,
    company: Optional[str] = None,
    location: Optional[str] = None,
    job_type: Optional[str] = None,
    experience_level: Optional[str] = None,
    min_date: Optional[str] = None,
    max_date: Optional[str] = None,
    limit: int = Query(10, le=100),
    skip: int = Query(0, ge=0),
    api_key: str = Depends(verify_api_key)
):
    """Search for jobs in the database with flexible parameters"""
    collection = get_jobs_collection()
    
    # Build query
    query = {}
    if q:
        # Full text search across all fields
        query["$text"] = {"$search": q}
    
    # Add specific field searches
    if title:
        query["job_title"] = {"$regex": title, "$options": "i"}
    if company:
        query["company"] = {"$regex": company, "$options": "i"}
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if job_type:
        query["job_type"] = {"$regex": job_type, "$options": "i"}
    if experience_level:
        query["experience_level"] = {"$regex": experience_level, "$options": "i"}
    
    # Date range filters if specified
    date_filter = {}
    if min_date:
        try:
            min_date_obj = datetime.fromisoformat(min_date.replace('Z', '+00:00'))
            date_filter["$gte"] = min_date_obj
        except:
            pass
    if max_date:
        try:
            max_date_obj = datetime.fromisoformat(max_date.replace('Z', '+00:00'))
            date_filter["$lte"] = max_date_obj
        except:
            pass
    if date_filter:
        query["metadata.scraped_at"] = date_filter
    
    # Execute query
    cursor = collection.find(query).skip(skip).limit(limit)
    jobs = await cursor.to_list(length=limit)
    
    # Convert MongoDB _id to string
    for job in jobs:
        job["_id"] = str(job["_id"])
        
    return jobs

@router.get("/{job_id}")
async def get_job(
    job_id: str = Path(..., description="Job ID in the database"),
    api_key: str = Depends(verify_api_key)
):
    """Get a specific job by ID"""
    # Implementation same as other routes
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query
from typing import Optional, List
import logging
from uuid import uuid4
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel, HttpUrl

from app.core.security import verify_api_key
from app.db.mongodb import get_profiles_collection, get_tasks_collection
from app.scrapers.profile_scraper import ProfileScraper
router = APIRouter()

# Configure logger
logger = logging.getLogger("profiles_logger")
logging.basicConfig(level=logging.INFO)
router = APIRouter()

class ProfileRequest(BaseModel):
    url: HttpUrl
    background: bool = True

@router.post("/scrape")
async def scrape_profile(
    request: ProfileRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Scrape a LinkedIn profile with proxy rotation"""
    # Create task in database first
    task_id = str(uuid4())
    task = {
        "_id": task_id,
        "type": "profile_scrape",
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
                scraper = ProfileScraper()
                result = await scraper.scrape_profile(str(url), task_id)
                
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
        background_tasks.add_task(scrape_with_error_handling, str(request.url), task_id)
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Scraping started in background"
        }
    else:
        # Run synchronously (not recommended for production)
        scraper = ProfileScraper()
        result = await scraper.scrape_profile(
            str(request.url), 
            task_id
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to scrape profile")
            
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
async def list_all_profiles(
    limit: int = Query(50, le=500),
    skip: int = Query(0, ge=0),
    api_key: str = Depends(verify_api_key)
):
    """Get all profiles in the database with pagination"""
    collection = get_profiles_collection()
    
    # Execute query with pagination
    cursor = collection.find().sort("metadata.scraped_at", -1).skip(skip).limit(limit)
    profiles = await cursor.to_list(length=limit)
    
    # Get total count for pagination info
    total = await collection.count_documents({})
    
    # Convert MongoDB _id to string
    for profile in profiles:
        profile["_id"] = str(profile["_id"])
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": profiles
    }

@router.get("/search")
async def search_profiles(
    q: Optional[str] = None,
    name: Optional[str] = None,
    headline: Optional[str] = None,
    skills: Optional[str] = None,
    company: Optional[str] = None,
    location: Optional[str] = None,
    university: Optional[str] = None,
    experience: Optional[str] = None,
    limit: int = Query(10, le=100),
    skip: int = Query(0, ge=0),
    api_key: str = Depends(verify_api_key)
):
    """Search for profiles in the database with flexible parameters"""
    collection = get_profiles_collection()
    
    # Build query
    query = {}
    if q:
        # Full text search across all fields
        query["$text"] = {"$search": q}
    
    # Add specific field searches
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if headline:
        query["headline"] = {"$regex": headline, "$options": "i"}
    if company:
        query["company"] = {"$regex": company, "$options": "i"}
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if skills:
        query["skills"] = {"$in": [{"$regex": skills, "$options": "i"}]}
    if university:
        query["educations.school"] = {"$regex": university, "$options": "i"}
    if experience:
        query["experiences.title"] = {"$regex": experience, "$options": "i"}
    
    # Execute query
    cursor = collection.find(query).skip(skip).limit(limit)
    profiles = await cursor.to_list(length=limit)
    
    # Convert MongoDB _id to string
    for profile in profiles:
        profile["_id"] = str(profile["_id"])
        
    return profiles

@router.get("/{profile_id}")
async def get_profile(
    profile_id: str = Path(..., description="Profile ID in the database"),
    api_key: str = Depends(verify_api_key)
):
    """Get a specific profile by ID"""
    collection = get_profiles_collection()
    
    try:
        profile = await collection.find_one({"_id": ObjectId(profile_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid profile ID format")
        
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    profile["_id"] = str(profile["_id"])
    return profile

@router.get("/task/{task_id}/result")
async def get_task_result(
    task_id: str = Path(..., description="Task ID of the scraping job"),
    api_key: str = Depends(verify_api_key)
):
    """Get the result data for a completed task"""
    tasks_collection = get_tasks_collection()
    task = await tasks_collection.find_one({"_id": task_id})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed. Current status: {task.get('status')}")
        
    result_id = task.get("result_id")
    if not result_id:
        raise HTTPException(status_code=400, detail="Task has no result ID")
        
    # Get the actual profile data
    profiles_collection = get_profiles_collection()
    profile = await profiles_collection.find_one({"_id": ObjectId(result_id)})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile result not found")
        
    profile["_id"] = str(profile["_id"])
    return profile
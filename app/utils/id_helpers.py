from fastapi import HTTPException
from bson import ObjectId, errors

def validate_object_id(id_str: str):
    """Validate and convert string to ObjectId"""
    try:
        return ObjectId(id_str)
    except (errors.InvalidId, TypeError):
        raise HTTPException(status_code=400, detail="Invalid ID format")

async def find_company_id_by_name(collection, name: str):
    """Helper to find company ID by name"""
    company = await collection.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
    if not company:
        return None
    return str(company["_id"])

async def find_job_id_by_title_and_company(collection, title: str, company: str):
    """Helper to find job ID by title and company"""
    job = await collection.find_one({
        "job_title": {"$regex": f"^{title}$", "$options": "i"},
        "company": {"$regex": f"^{company}$", "$options": "i"}
    })
    if not job:
        return None
    return str(job["_id"])
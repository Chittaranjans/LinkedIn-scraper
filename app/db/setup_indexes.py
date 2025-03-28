import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logger = logging.getLogger("app.db.indexes")

async def setup_indexes():
    """Set up indexes for MongoDB collections"""
    print("Setting up MongoDB indexes...")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    
    # Create text indexes for full-text search
    try:
        # First check if text index already exists on companies collection
        existing_indexes = await db.companies.list_indexes().to_list(None)
        has_text_index = False
        
        for idx in existing_indexes:
            if "text" in idx.get("name", ""):
                has_text_index = True
                print(f"Text index already exists on companies collection: {idx['name']}")
                break
        
        # Only create if no text index exists
        if not has_text_index:
            await db.companies.create_index([
                ("name", "text"),
                ("industry", "text"),
                ("description", "text"),
                ("location", "text"),
                ("website", "text")
            ])
            print("Created text index on companies collection")
    except Exception as e:
        print(f"Error creating companies text index: {str(e)}")
        # Continue with other indexes
    
    # Similar approach for jobs
    try:
        existing_indexes = await db.jobs.list_indexes().to_list(None)
        has_text_index = False
        
        for idx in existing_indexes:
            if "text" in idx.get("name", ""):
                has_text_index = True
                print(f"Text index already exists on jobs collection: {idx['name']}")
                break
                
        if not has_text_index:
            await db.jobs.create_index([
                ("job_title", "text"),
                ("company", "text"),
                ("description", "text"),
                ("location", "text"),
                ("requirements", "text")
            ])
            print("Created text index on jobs collection")
    except Exception as e:
        print(f"Error creating jobs text index: {str(e)}")
    
    # Similar approach for profiles
    try:
        existing_indexes = await db.profiles.list_indexes().to_list(None)
        has_text_index = False
        
        for idx in existing_indexes:
            if "text" in idx.get("name", ""):
                has_text_index = True
                print(f"Text index already exists on profiles collection: {idx['name']}")
                break
                
        if not has_text_index:
            await db.profiles.create_index([
                ("name", "text"),
                ("headline", "text"),
                ("about", "text"),
                ("location", "text"),
                ("skills", "text"),
                ("company", "text")
            ])
            print("Created text index on profiles collection")
    except Exception as e:
        print(f"Error creating profiles text index: {str(e)}")
    
    # Create other regular indexes - these can coexist with existing ones
    try:
        # Companies regular indexes
        await db.companies.create_index("name")
        await db.companies.create_index("industry")
        await db.companies.create_index("location")
        
        # Jobs regular indexes
        await db.jobs.create_index("job_title")
        await db.jobs.create_index("company")
        await db.jobs.create_index("location")
        await db.jobs.create_index("job_type")
        
        # Profiles regular indexes
        await db.profiles.create_index("name")
        await db.profiles.create_index("skills")
        await db.profiles.create_index("location")
        await db.profiles.create_index("company")
        
        # Create index on scraped_at for sorting
        await db.companies.create_index([("metadata.scraped_at", -1)])
        await db.jobs.create_index([("metadata.scraped_at", -1)])
        await db.profiles.create_index([("metadata.scraped_at", -1)])
        
        print("Regular indexes created successfully")
    except Exception as e:
        print(f"Error creating regular indexes: {str(e)}")
    
    print("MongoDB indexes setup completed")

# Run this script directly to set up indexes
if __name__ == "__main__":
    asyncio.run(setup_indexes())
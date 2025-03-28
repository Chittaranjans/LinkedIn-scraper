import logging
import motor.motor_asyncio
import certifi
import sys
from app.core.config import settings

logger = logging.getLogger("app.db")
client = None
db = None

async def connect_to_mongo():
    global client, db
    try:
        # Get Python version
        is_python_313 = sys.version_info.major == 3 and sys.version_info.minor >= 13
        
        # Special handling for Python 3.13+
        if is_python_313:
            # Extract and construct URL properly
            connection_parts = settings.MONGODB_URL.split('@')
            if len(connection_parts) > 1:
                credentials = connection_parts[0].replace('mongodb+srv://', '')
                
                # Extract the correct replica set name from your cluster
                # For MongoDB Atlas, this is typically "atlas-[cluster-id]"
                # Instead of hardcoding, try without specifying it
                
                hosts = [
                    f"cluster0-shard-00-00.twlvh.mongodb.net:27017",
                    f"cluster0-shard-00-01.twlvh.mongodb.net:27017",
                    f"cluster0-shard-00-02.twlvh.mongodb.net:27017"
                ]
                host_string = ','.join(hosts)
                
                # Remove the hardcoded replica set name
                direct_url = f"mongodb://{credentials}@{host_string}/?ssl=true&authSource=admin&retryWrites=true&w=majority"
                
                logger.info("Using direct connection for Python 3.13+")
                
                # Connect with minimal options
                client = motor.motor_asyncio.AsyncIOMotorClient(
                    direct_url,
                    tlsCAFile=certifi.where(),
                    tlsAllowInvalidCertificates=True,  # Only for development
                    serverSelectionTimeoutMS=30000  # Increase timeout
                )
            else:
                # Fallback to original URL with minimal parameters
                client = motor.motor_asyncio.AsyncIOMotorClient(
                    settings.MONGODB_URL,
                    tlsAllowInvalidCertificates=True,  # Only for development
                    serverSelectionTimeoutMS=30000
                )
        else:
            # Regular connection for Python ≤ 3.12
            client = motor.motor_asyncio.AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=60000,
                tlsCAFile=certifi.where()
            )
        
        # Test connection immediately
        await client.admin.command('ping')
        db = client[settings.MONGODB_DB_NAME]
        
        # Create indexes for faster queries
        #await create_indexes()
        
        logger.info("Connected to MongoDB Atlas successfully")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise

# async def create_indexes():
#     """Create necessary indexes for MongoDB collections"""
#     try:
#         # Company collection indexes
#         await get_companies_collection().create_index([("JobDetails.companyInfo.name", "text"), 
#                                                     ("JobDetails.companyInfo.description.text", "text")])
#         await get_companies_collection().create_index("JobDetails.companyInfo.industry")
        
#         # Job collection indexes
#         await get_jobs_collection().create_index([("job_title", "text"), ("job_description", "text")])
#         await get_jobs_collection().create_index("company")
#         await get_jobs_collection().create_index("location")
        
#         # Profile collection indexes
#         await get_profiles_collection().create_index([("name", "text"), ("about", "text")])
#         await get_profiles_collection().create_index("skills")
        
#         logger.info("MongoDB indexes created successfully")
#     except Exception as e:
#         logger.error(f"Error creating MongoDB indexes: {str(e)}")

async def close_mongo_connection():
    global client
    if client:
        client.close()
        logger.info("Closed MongoDB connection")

def get_companies_collection():
    return db["companies"]

def get_profiles_collection():
    return db["profiles"]

def get_jobs_collection():
    return db["jobs"]

def get_tasks_collection():
    return db["tasks"]
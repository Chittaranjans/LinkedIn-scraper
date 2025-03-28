from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.api.routes import companies, profiles, jobs
from app.core.config import settings
from app.core.middleware import RateLimitMiddleware
from app.db.setup_indexes import setup_indexes

app = FastAPI(
    title="LinkedIn Scraper API",
    description="Production-ready LinkedIn scraping API with proxy rotation",
    version="1.0.0"
)

# Connect to MongoDB on startup
@app.on_event("startup")
async def startup():
    await connect_to_mongo()
    # Set up MongoDB indexes
    await setup_indexes()

@app.on_event("shutdown")
async def shutdown():
    await close_mongo_connection()

# Add middlewares
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routes
app.include_router(companies.router, prefix="/api/companies", tags=["companies"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])

# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "LinkedIn Scraper API"}
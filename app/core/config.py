from pydantic_settings import BaseSettings
import os
from typing import List

class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "LinkedIn Scraper API"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development_secret_key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # MongoDB settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "linkedin_data")
    
    # LinkedIn credentials
    LINKEDIN_USER: str = os.getenv("LINKEDIN_USER", "")
    LINKEDIN_PASSWORD: str = os.getenv("LINKEDIN_PASSWORD", "")
    
    # Rate limiting
    RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", "60"))  # requests per minute
    
    # Security
    API_KEYS: List[str] = os.getenv("API_KEYS", "test_api_key").split(",")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    class Config:
        env_file = ".env"

settings = Settings()
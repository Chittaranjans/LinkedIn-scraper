import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# LinkedIn credentials
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
LINKEDIN_COOKIE = os.getenv("LINKEDIN_COOKIE", None)

# Proxy configuration
PROXY_LIST = [
    proxy.strip() for proxy in os.getenv("PROXY_LIST", "").split(",") if proxy.strip()
]
USE_PROXIES = len(PROXY_LIST) > 0

# Scraping settings
WAIT_TIME = 3  # Time to wait between requests
MAX_RETRIES = 3  # Maximum number of retries for failed requests

# Target data
COMPANY_URLS = [
    "https://www.linkedin.com/company/accenture/",
    "https://www.linkedin.com/company/microsoft/",
    # Add more company URLs as needed
]

JOB_KEYWORDS = [
    "software engineer",
    "data scientist",
    # Add more job search keywords as needed
]

PROFILE_URLS = [
    "https://www.linkedin.com/in/satyanadella/",
    # Add more profile URLs as needed
]

# Output settings
OUTPUT_FOLDER = "scraped_data"
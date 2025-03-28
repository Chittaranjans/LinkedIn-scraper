import asyncio
import random
from datetime import datetime
import logging
import traceback
import time
from bson import ObjectId

from app.db.mongodb import get_companies_collection, get_tasks_collection
from utils.proxy_handler import ProxyHandler
from utils.cookie_auth import LinkedInCookieAuth
from linkedin_scraper.custom_company_scraper import CustomCompanyScraper
from dataformatter.data_formatter import LinkedInFormatter
import os
from dotenv import load_dotenv

load_dotenv()
LINKEDIN_USER = os.getenv('LINKEDIN_USER')
LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD')

logger = logging.getLogger("app.scraper")

class CompanyScraper:
    """Production-ready LinkedIn company scraper with proxy rotation"""
    
    def __init__(self, proxy_file='utils/proxies.txt', headless=False):
        self.proxy_handler = ProxyHandler(proxy_file=proxy_file)
        self.driver = None
        self.current_proxy = None
        self.headless = True
        self.company_cache = {}
        self.formatter = LinkedInFormatter()  # Initialize formatter
        self.auth = None  # Will be initialized during setup_driver
    
        
    async def setup_driver(self):
        """Initialize or refresh the WebDriver with a new proxy"""
        # Close existing driver if any
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        # Create new driver with proxy using run_in_executor for async compatibility
        loop = asyncio.get_event_loop()
        self.driver, self.current_proxy = await loop.run_in_executor(
            None,
            lambda: self.proxy_handler.create_driver(use_proxy=True, headless=True)  # Force headless=True for server
        )
        
        if not self.driver:
            # If proxy failed, try without proxy as fallback
            logger.warning("Failed to create driver with proxy. Trying without proxy.")
            self.driver, _ = await loop.run_in_executor(
                None,
                lambda: self.proxy_handler.create_driver(use_proxy=False, headless=True)  # Force headless=True for server
            )
            
        if self.driver:
            # Initialize authentication helper
            self.auth = LinkedInCookieAuth(self.driver)
            
        return self.driver is not None

    async def authenticate(self):
        """Improved authentication with better error handling"""
        if not self.driver or not self.auth:
            logger.error("Driver or auth not initialized")
            return False
        
        # First try with direct connection (no proxy) for authentication
        original_proxy = self.current_proxy
        original_driver = self.driver
        
        try:
            logger.info("Creating direct connection for authentication")
            loop = asyncio.get_event_loop()
            self.driver, _ = await loop.run_in_executor(
                None,
                lambda: self.proxy_handler.create_driver(use_proxy=False, headless=True)  # Force headless=True for server
            )
            self.auth = LinkedInCookieAuth(self.driver)
            
            # Try cookie authentication
            if os.path.exists(self.auth.cookie_file):
                logger.info(f"Attempting login with cookies from {self.auth.cookie_file}")
                auth_result = await loop.run_in_executor(
                    None,
                    lambda: self.auth.load_cookies(self.driver) and self.auth.verify_login(self.driver)
                )
                if auth_result:
                    logger.info("Successfully authenticated with cookies")
                    return True
            
            # If cookie auth fails, try credentials
            if LINKEDIN_USER and LINKEDIN_PASSWORD:
                logger.info("Attempting login with credentials")
                result = await loop.run_in_executor(
                    None,
                    lambda: self.auth.authenticate_with_credentials(LINKEDIN_USER, LINKEDIN_PASSWORD)
                )
                if result:
                    logger.info("Successfully logged in with credentials")
                    # Save cookies for future use
                    await loop.run_in_executor(
                        None,
                        lambda: self.auth.save_cookies(driver=self.driver)
                    )
                    return True
                    
            # If direct connection fails, try with proxy as fallback
            if original_proxy:
                logger.info(f"Trying authentication with original proxy: {original_proxy}")
                await loop.run_in_executor(None, lambda: self.driver.quit() if self.driver else None)
                self.driver = original_driver
                self.auth = LinkedInCookieAuth(self.driver)
                
                # Try credentials with proxy
                if LINKEDIN_USER and LINKEDIN_PASSWORD:
                    result = await loop.run_in_executor(
                        None,
                        lambda: self.auth.authenticate_with_credentials(LINKEDIN_USER, LINKEDIN_PASSWORD)
                    )
                    if result:
                        logger.info("Successfully logged in with credentials using proxy")
                        return True
                        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Restore original driver if needed
            if self.driver != original_driver:
                try:
                    await loop.run_in_executor(None, lambda: self.driver.quit() if self.driver else None)
                except:
                    pass
                self.driver = original_driver
                self.auth = LinkedInCookieAuth(self.driver)
        
        logger.error("All authentication methods failed")
        return False

        
    async def scrape_company(self, url, task_id=None, include_employees=True):
        """Scrape company with retry logic and proxy rotation"""
        max_retries = 3
        retries = 0
        
        # Update task to "in_progress" immediately
        await self.update_task(task_id, "in_progress", error=None)
        
        # Add timeout protection
        start_time = time.time()
        max_execution_time = 300  # 5 minutes max per company
        
        while retries < max_retries:
            try:
                # Check timeout
                if time.time() - start_time > max_execution_time:
                    await self.update_task(task_id, "failed", error="Task timed out after 5 minutes")
                    logger.error(f"Scraping timed out for {url}")
                    return None

                # Setup driver
                if not await self.setup_driver():
                    await self.update_task(task_id, "failed", error="Failed to initialize WebDriver")
                    return None
                    
                # Authenticate
                if not await self.authenticate():
                    await self.update_task(task_id, "failed", error="Authentication failed")
                    return None
                    
                # Run the scraping
                logger.info(f"Scraping company: {url}, attempt {retries+1}/{max_retries}")
                loop = asyncio.get_event_loop()
                
                # Create scraper and run
                custom_scraper = CustomCompanyScraper(self.driver)
                company_data = await loop.run_in_executor(
                    None,
                    lambda: custom_scraper.scrape_company(url)
                )
                
                # More frequent status updates
                await self.update_task(task_id, "processing", error=None)
                
                if company_data:
                    # Insert into MongoDB
                    company_data["metadata"] = {
                        "scraped_at": datetime.now(),
                        "url": url,
                        "task_id": str(task_id) if task_id else None
                    }
                    
                    collection = get_companies_collection()
                    result = await collection.insert_one(company_data)
                    
                    # Update task status
                    await self.update_task(task_id, "completed", result_id=result.inserted_id)
                    
                    # Return the scraped data
                    company_data["_id"] = str(result.inserted_id)
                    logger.info(f"Successfully scraped company: {url}")
                    return company_data
                    
                logger.warning(f"No data returned for {url}")
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Mark current proxy as failed
                if self.current_proxy:
                    await loop.run_in_executor(
                        None,
                        lambda: self.proxy_handler.mark_proxy_as_failed(self.current_proxy)
                    )
                    
                # Retry with new proxy
                retries += 1
                if retries < max_retries:
                    logger.info(f"Retrying with new proxy (attempt {retries+1}/{max_retries})")
                    # Use exponential backoff
                    delay = 2 ** retries + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Max retries reached for {url}")
                    await self.update_task(task_id, "failed", error=f"Failed after {max_retries} attempts")
                    
        return None
        
    async def update_task(self, task_id, status, result_id=None, error=None):
        """Update task status in MongoDB"""
        if not task_id:
            return
            
        tasks_collection = get_tasks_collection()
        update_data = {
            "status": status,
            "updated_at": datetime.now()
        }
        
        if result_id:
            update_data["result_id"] = str(result_id)
        
        if error:
            update_data["error"] = error
            
        # Don't try to convert string UUID to ObjectId
        await tasks_collection.update_one(
            {"_id": task_id},
            {"$set": update_data}
        )
        
    def __del__(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
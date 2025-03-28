import asyncio
from datetime import datetime
import logging
import traceback
from bson import ObjectId

from app.db.mongodb import get_profiles_collection, get_tasks_collection
from utils.proxy_handler import ProxyHandler
from utils.cookie_auth import LinkedInCookieAuth
from linkedin_scraper import Person
from dataformatter.data_formatter import LinkedInFormatter

logger = logging.getLogger("app.scraper")

class ProfileScraper:
    """Production-ready LinkedIn profile scraper with proxy rotation"""
    
    def __init__(self):
        self.proxy_handler = ProxyHandler()
        self.driver = None
        self.current_proxy = None
        self.headless = True  # Always headless in production
        self.formatter = LinkedInFormatter()


    async def setup_driver(self):
        """Initialize WebDriver with proxy rotation"""
        # Close existing driver if any
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
                
        # Create new driver with proxy
        loop = asyncio.get_event_loop()
        self.driver, self.current_proxy = await loop.run_in_executor(
            None, 
            lambda: self.proxy_handler.create_driver(use_proxy=True, headless=self.headless)
        )
        
        if not self.driver:
            logger.warning("Failed to create driver with proxy. Trying without proxy.")
            self.driver, _ = await loop.run_in_executor(
                None,
                lambda: self.proxy_handler.create_driver(use_proxy=False, headless=self.headless)
            )
        
        return self.driver is not None
        
    async def authenticate(self):
        """Authenticate with LinkedIn"""
        if not self.driver:
            return False
            
        from app.core.config import settings
        
        auth = LinkedInCookieAuth(self.driver)
        loop = asyncio.get_event_loop()
        
        # Try cookie auth first
        try:
            result = await loop.run_in_executor(None, lambda: auth.authenticate_with_cookies())
            if result:
                logger.info("Successfully authenticated with cookies")
                return True
        except Exception as e:
            logger.error(f"Cookie authentication failed: {str(e)}")
        
        # Try credentials if available
        if settings.LINKEDIN_USER and settings.LINKEDIN_PASSWORD:
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: auth.get_manual_login(self.driver, settings.LINKEDIN_USER, settings.LINKEDIN_PASSWORD)
                )
                if result:
                    logger.info("Successfully authenticated with credentials")
                    return True
            except Exception as e:
                logger.error(f"Credentials authentication failed: {str(e)}")
                
        return False
        
    async def scrape_profile(self, url, task_id=None):
        """Scrape profile with retry logic and proxy rotation"""
        max_retries = 3
        retries = 0
        
        while retries < max_retries:
            try:
                # Setup driver
                if not await self.setup_driver():
                    await self.update_task(task_id, "failed", error="Failed to initialize WebDriver")
                    return None
                    
                # Authenticate
                if not await self.authenticate():
                    await self.update_task(task_id, "failed", error="Authentication failed")
                    return None
                    
                # Run the scraping
                logger.info(f"Scraping profile: {url}, attempt {retries+1}/{max_retries}")
                loop = asyncio.get_event_loop()
                
                # Use Person class to scrape
                profile_data = await loop.run_in_executor(
                    None,
                    lambda: self._scrape_profile(url)
                )
                
                if profile_data:
                    # Insert into MongoDB
                    profile_data["metadata"] = {
                        "scraped_at": datetime.now(),
                        "url": url,
                        "task_id": task_id
                    }
                    
                    collection = get_profiles_collection()
                    result = await collection.insert_one(profile_data)
                    
                    # Update task status
                    await self.update_task(task_id, "completed", result_id=result.inserted_id)
                    
                    # Return the scraped data
                    profile_data["_id"] = str(result.inserted_id)
                    return profile_data
                    
                logger.warning(f"No data returned for {url}")
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Mark current proxy as failed
                if self.current_proxy:
                    self.proxy_handler.mark_proxy_as_failed(self.current_proxy)
                    
                # Retry with new proxy
                retries += 1
                if retries < max_retries:
                    logger.info(f"Retrying with new proxy (attempt {retries+1}/{max_retries})")
                    await asyncio.sleep(2)  # Short delay before retry
                else:
                    logger.error(f"Max retries reached for {url}")
                    await self.update_task(task_id, "failed", error=f"Failed after {max_retries} attempts")
                    
        return None
    
    def _scrape_profile(self, url):
        """Execute actual profile scraping using Person class"""
        try:
            person = Person(
                linkedin_url=url,
                driver=self.driver,
                close_on_complete=False,
                scrape=True
            )
            
            # Format data
            profile_data = self.formatter.format_profile_data(person)
            #self.profiles.append(profile_data)
            
            
            logger.info(f"Successfully scraped profile: {profile_data['name']}")
            
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error in _scrape_profile: {str(e)}")
            logger.error(traceback.format_exc())
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
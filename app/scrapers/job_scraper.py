import asyncio
import os
import time
import random
from datetime import datetime
import logging
import traceback
from bson import ObjectId

from app.db.mongodb import get_jobs_collection, get_tasks_collection
from utils.proxy_handler import ProxyHandler
from utils.cookie_auth import LinkedInCookieAuth
from linkedin_scraper.custom_job_scraper import CustomJobScraper
from linkedin_scraper.company_scraper_integration import CompanyScraperIntegration
from dataformatter.job_formatter import JobFormatter
from dataformatter.data_formatter import LinkedInFormatter

logger = logging.getLogger("app.scraper")

class JobScraper:
    """Production-ready LinkedIn job scraper with proxy rotation"""
    
    def __init__(self, save_to_file=False, output_dir='scraped_data'):
        self.proxy_handler = ProxyHandler()
        self.driver = None
        self.current_proxy = None
        self.headless = True  # Always headless in production
        self.save_to_file = save_to_file
        self.output_dir = output_dir
        
        # Initialize formatters
        self.job_formatter = JobFormatter(output_dir=output_dir)
        self.data_formatter = LinkedInFormatter()
        
        # Create output directory if needed
        if save_to_file:
            os.makedirs(output_dir, exist_ok=True)
        
    async def setup_driver(self):
        """Initialize WebDriver with proxy rotation and timeout protection"""
        # Add timeout to prevent stuck drivers
        try:
            return await asyncio.wait_for(
                self._setup_driver_internal(), 
                timeout=30.0  # 30 second timeout for driver setup
            )
        except asyncio.TimeoutError:
            logger.error("Driver setup timed out")
            return False
        
    async def _setup_driver_internal(self):
        """Internal method for setting up WebDriver"""
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
        """Authenticate to LinkedIn with cookies or login"""
        if not self.driver:
            return False
            
        from app.core.config import settings
        
        auth = LinkedInCookieAuth(self.driver)
        loop = asyncio.get_event_loop()
        
        # Try cookie auth first
        try:
            # Check if cookies file exists and load them
            cookie_result = await loop.run_in_executor(
                None,
                lambda: auth.load_cookies(self.driver) and auth.verify_login(self.driver)
            )
            if cookie_result:
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
            
    async def update_task(self, task_id, status, result_id=None, result_ids=None, count=None, error=None):
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
            
        if result_ids:
            update_data["result_ids"] = [str(id) for id in result_ids]
            
        if count is not None:
            update_data["count"] = count
        
        if error:
            update_data["error"] = error
            
        await tasks_collection.update_one(
            {"_id": task_id},
            {"$set": update_data}
        )
        
    async def search_jobs(self, keywords, location=None, limit=20, task_id=None, include_company_data=True):
        """Search and scrape jobs with retry logic and proxy rotation"""
        max_retries = 3
        retries = 0
        
        # Update task to in_progress immediately
        await self.update_task(task_id, "in_progress", error=None)
        
        while retries < max_retries:
            try:
                # Setup driver if needed
                if not self.driver:
                    if not await self.setup_driver():
                        await self.update_task(task_id, "failed", error="Failed to initialize WebDriver")
                        return None
                    
                # Authenticate with LinkedIn
                if not await self.authenticate():
                    await self.update_task(task_id, "failed", error="Authentication failed")
                    return None
                    
                # Run the scraping
                logger.info(f"Searching jobs: '{keywords}' in {location}, attempt {retries+1}/{max_retries}")
                loop = asyncio.get_event_loop()
                
                # Initialize our custom job scraper
                job_scraper = CustomJobScraper(self.driver)
                
                # Initialize company scraper integration if needed
                if include_company_data:
                    company_scraper = CompanyScraperIntegration(self.driver, self.data_formatter)
                
                # Get basic job data from search results
                job_results = await loop.run_in_executor(
                    None,
                    lambda: job_scraper.search_jobs(keywords, location, limit)
                )
                
                logger.info(f"Found {len(job_results)} job results for '{keywords}' in {location}")
                
                if job_results:
                    # Process jobs with details
                    detailed_jobs = []
                    for job_data in job_results:
                        try:
                            # Get detailed job info
                            detailed_job = await loop.run_in_executor(
                                None,
                                lambda: job_scraper.get_job_details(job_data)
                            )
                            
                            # Add company data if requested
                            if include_company_data:
                                # Generate company URL from company name
                                company_name = detailed_job.get("company", "")
                                if company_name:
                                    # Generate URL directly from name
                                    company_url = await loop.run_in_executor(
                                        None,
                                        lambda: company_scraper.url_extractor.generate_url_from_name(company_name)
                                    )
                                    
                                    if company_url:
                                        detailed_job["company_linkedin_url"] = company_url
                                        logger.info(f"Generated company URL from name: {company_url}")
                                        
                                        # Get company details for the job
                                        detailed_job = await loop.run_in_executor(
                                            None,
                                            lambda: company_scraper.scrape_company_for_job(detailed_job)
                                        )
                            
                            # Format job data
                            formatted_job = self.job_formatter.format_job_data(detailed_job)
                            
                            # Add metadata
                            formatted_job["metadata"] = {
                                "scraped_at": datetime.now(),
                                "search_keywords": keywords,
                                "search_location": location,
                                "task_id": task_id
                            }
                            
                            detailed_jobs.append(formatted_job)
                            logger.info(f"Successfully scraped job: {formatted_job['job_title']}")
                            
                            # Add delay between jobs
                            await asyncio.sleep(random.uniform(1, 3))
                            
                        except Exception as e:
                            logger.error(f"Error processing job: {str(e)}")
                            logger.error(traceback.format_exc())
                    
                    # Save to file if requested
                    if self.save_to_file and detailed_jobs:
                        search_term_filename = f"jobs_{keywords.replace(' ', '_')}_{location.replace(' ', '_')}".lower()
                        await loop.run_in_executor(
                            None,
                            lambda: self.job_formatter.save_to_json(detailed_jobs, search_term_filename)
                        )
                    
                    # Save to MongoDB
                    if detailed_jobs:
                        collection = get_jobs_collection()
                        result = await collection.insert_many(detailed_jobs)
                        
                        # Update task status
                        await self.update_task(
                            task_id, 
                            "completed",
                            result_ids=result.inserted_ids if result else None,
                            count=len(detailed_jobs)
                        )
                        
                        # Add MongoDB IDs to the job data
                        for i, job in enumerate(detailed_jobs):
                            if result and i < len(result.inserted_ids):
                                job["_id"] = str(result.inserted_ids[i])
                        
                        return detailed_jobs
                
                # If we got here with no jobs, log a warning
                logger.warning(f"No jobs found for '{keywords}' in {location}")
                await self.update_task(task_id, "completed", count=0)
                return []
                
            except Exception as e:
                logger.error(f"Error searching jobs: {str(e)}")
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
                    logger.error(f"Max retries reached for job search")
                    await self.update_task(task_id, "failed", error=f"Failed after {max_retries} attempts")
                    
        return None
    
    async def scrape_job(self, url, task_id=None, include_company_data=True):
        """Scrape a specific job with retry logic and proxy rotation"""
        max_retries = 3
        retries = 0
        
        # Update task to in_progress immediately
        await self.update_task(task_id, "in_progress", error=None)
        
        while retries < max_retries:
            try:
                # Setup driver if needed
                if not self.driver:
                    if not await self.setup_driver():
                        await self.update_task(task_id, "failed", error="Failed to initialize WebDriver")
                        return None
                    
                # Authenticate with LinkedIn
                if not await self.authenticate():
                    await self.update_task(task_id, "failed", error="Authentication failed")
                    return None
                    
                # Run the scraping
                logger.info(f"Scraping job: {url}, attempt {retries+1}/{max_retries}")
                loop = asyncio.get_event_loop()
                
                # Initialize scrapers
                job_scraper = CustomJobScraper(self.driver)
                
                # Use CustomJobScraper to get job details
                job_data = await loop.run_in_executor(
                    None,
                    lambda: job_scraper.get_job_details({"linkedin_url": url})
                )
                
                if job_data:
                    # Add company data if requested
                    if include_company_data:
                        company_scraper = CompanyScraperIntegration(self.driver, self.data_formatter)
                        
                        # Generate company URL if it's missing
                        if "company" in job_data and not job_data.get("company_linkedin_url"):
                            company_name = job_data["company"]
                            company_url = await loop.run_in_executor(
                                None,
                                lambda: company_scraper.url_extractor.generate_url_from_name(company_name)
                            )
                            
                            if company_url:
                                job_data["company_linkedin_url"] = company_url
                                logger.info(f"Generated company URL from name: {company_url}")
                        
                        # Get company details
                        if job_data.get("company_linkedin_url"):
                            job_data = await loop.run_in_executor(
                                None,
                                lambda: company_scraper.scrape_company_for_job(job_data)
                            )
                    
                    # Format job data
                    formatted_job = self.job_formatter.format_job_data(job_data)
                    
                    # Add metadata
                    formatted_job["metadata"] = {
                        "scraped_at": datetime.now(),
                        "url": url,
                        "task_id": task_id
                    }
                    
                    # Save to file if requested
                    if self.save_to_file:
                        job_title = formatted_job.get("job_title", "").replace(" ", "_").lower()
                        company = formatted_job.get("company", "").replace(" ", "_").lower()
                        filename = f"job_{job_title}_{company}"
                        await loop.run_in_executor(
                            None,
                            lambda: self.job_formatter.save_to_json([formatted_job], filename)
                        )
                    
                    # Save to MongoDB
                    collection = get_jobs_collection()
                    result = await collection.insert_one(formatted_job)
                    
                    # Update task status
                    await self.update_task(task_id, "completed", result_id=result.inserted_id)
                    
                    # Add MongoDB ID to the job data
                    formatted_job["_id"] = str(result.inserted_id)
                    return formatted_job
                    
                logger.warning(f"No data returned for job {url}")
                await self.update_task(task_id, "completed", count=0)
                return None
                
            except Exception as e:
                logger.error(f"Error scraping job {url}: {str(e)}")
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
                    logger.error(f"Max retries reached for job {url}")
                    await self.update_task(task_id, "failed", error=f"Failed after {max_retries} attempts")
                    
        return None
        
    def __del__(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
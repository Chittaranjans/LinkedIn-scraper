import logging
import time
import re
from linkedin_scraper.custom_company_scraper import CustomCompanyScraper
from linkedin_scraper.company_url_extractor import CompanyUrlExtractor
from dataformatter.data_formatter import LinkedInFormatter
from utils.logging_config import LoggingConfig

# Set up logging
logger = LoggingConfig.setup_logging("company_scraper_integration")

class CompanyScraperIntegration:
    def __init__(self, driver, formatter=None):
        self.driver = driver
        self.company_scraper = CustomCompanyScraper(driver)
        self.url_extractor = CompanyUrlExtractor(driver)
        self.formatter = formatter if formatter else LinkedInFormatter()
        self.company_cache = {}  # Cache to avoid re-scraping the same companies
    
    def generate_company_url(self, company_name):
        """Generate a potential LinkedIn company URL from a company name"""
        if not company_name:
            return None
            
        # Clean company name - remove Ltd, LLC, Inc, etc.
        clean_name = re.sub(r'\s+(?:Ltd|LLC|Inc|Corp|Limited|Corporation|Company)\.?$', '', company_name, flags=re.IGNORECASE)
        
        # Replace spaces with hyphens and convert to lowercase
        url_name = clean_name.lower().strip()
        url_name = re.sub(r'\s+', '-', url_name)  # Replace spaces with hyphens
        url_name = re.sub(r'[^\w\-]', '', url_name)  # Remove special chars except hyphens
        
        # Build URL
        company_url = f"https://www.linkedin.com/company/{url_name}/"
        logger.info(f"Generated company URL: {company_url} from name: {company_name}")
        
        return company_url
        
    def scrape_company_for_job(self, job_data):
        """Scrape company details for a job and attach to job data"""
        company_name = job_data.get("company", "")
        
        # Get company URL directly from name
        if not job_data.get("company_linkedin_url") or not job_data.get("company_linkedin_url").strip():
            company_url = self.url_extractor.generate_url_from_name(company_name)
            if company_url:
                job_data["company_linkedin_url"] = company_url
                logger.info(f"Generated company URL: {company_url} from name: {company_name}")
        else:
            company_url = job_data.get("company_linkedin_url")
        
        # If still no company URL, log and return
        if not company_url:
            logger.warning(f"Could not generate company URL for: {company_name}")
            return job_data
        
        # Check if we already scraped this company
        if company_url in self.company_cache:
            logger.info(f"Using cached company data for {company_name}")
            job_data["company_data"] = self.company_cache[company_url]
            return job_data
            
        logger.info(f"Scraping company details for job: {job_data.get('job_title')} at {company_name}")
        
        try:
            # Current tab has the job details, so open company page in a new tab
            original_window = self.driver.current_window_handle
            
            # Open a new window
            self.driver.execute_script("window.open('');")
            
            # Switch to the new window
            self.driver.switch_to.window(self.driver.window_handles[1])
            
            # Scrape the company
            company_data_dict = self.company_scraper.scrape_company(company_url)
            
            # Format the data for job listings - extract simplified company data
            if company_data_dict and "raw_data" in company_data_dict:
                raw_data = company_data_dict["raw_data"]
                # Extract the most important information for job listings
                simplified_company = {
                    "name": raw_data.get("name", ""),
                    "industry": raw_data.get("industry", ""),
                    "company_size": raw_data.get("company_size", ""),
                    "headquarters": raw_data.get("headquarters", ""),
                    "founded": raw_data.get("founded", ""),
                    "website": raw_data.get("website", ""),
                    "phone": raw_data.get("phone", ""),
                    "about_us": raw_data.get("about_us", ""),
                    "specialties": raw_data.get("specialties", ""),
                    "linkedin_url": company_url,
                    "logo": company_data_dict.get("JobDetails", {}).get("companyInfo", {}).get("logo", ""),
                    "leadership": company_data_dict.get("JobDetails", {}).get("companyInfo", {}).get("leadership", [])
                }
                
                # Cache the company data
                self.company_cache[company_url] = simplified_company
                
                # Add to job data
                job_data["company_data"] = simplified_company
            
            # Close the tab and go back to job details tab
            self.driver.close()
            self.driver.switch_to.window(original_window)
            
            logger.info(f"Successfully added company details for job at {company_name}")
            
        except Exception as e:
            logger.error(f"Error scraping company for job at {company_name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                # Make sure to return to original tab if there was an error
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(original_window)
            except:
                pass
                
        return job_data
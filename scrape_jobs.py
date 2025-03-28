import os
import time
import random
import logging
from dotenv import load_dotenv

# Import our custom modules
from utils.cookie_auth import LinkedInCookieAuth
from utils.browser_setup import BrowserSetup
from dataformatter.job_formatter import JobFormatter
from linkedin_scraper.custom_job_scraper import CustomJobScraper
from linkedin_scraper.company_scraper_integration import CompanyScraperIntegration
from dataformatter.data_formatter import LinkedInFormatter
from utils.logging_config import LoggingConfig

# Set up logging
logger = LoggingConfig.setup_logging("linkedin_job_scraper", "linkedin_jobs.log")


# Load environment variables
load_dotenv()
LINKEDIN_USER = os.getenv('LINKEDIN_USER')
LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD')

# Define job search terms
JOB_SEARCH_TERMS = [
    "python",
]

# Define locations (optional)
LOCATIONS = [
    "India"  # Add more locations if needed
]

def main():
    browser_setup = BrowserSetup()
    
    job_formatter = JobFormatter()
    
    # Initialize browser
    logger.info("Initializing browser...")
    driver = browser_setup.create_driver(use_proxy=False)
    if not driver:
        logger.error("Failed to create browser")
        return False
    auth_helper = LinkedInCookieAuth(driver)
    # Authenticate
    logger.info("Starting authentication process")
    cookie_login_successful = False
    if os.path.exists('cookies/linkedin_cookies.pkl'):
        logger.info("Attempting to login with saved cookies")
        auth_helper.load_cookies(driver)
        cookie_login_successful = auth_helper.verify_login(driver)
    
    # If cookie login fails, try manual login
    if not cookie_login_successful:
        logger.info("Cookie login failed, trying manual login")
        cookie_login_successful = auth_helper.get_manual_login(
            driver, 
            LINKEDIN_USER, 
            LINKEDIN_PASSWORD
        )
    
    if not cookie_login_successful:
        logger.error("Authentication failed. Cannot continue.")
        driver.quit()
        return False
    
    # Initialize our custom job scraper
    job_scraper = CustomJobScraper(driver)
    
    # Initialize company scraper integration
    data_formatter = LinkedInFormatter()
    company_scraper = CompanyScraperIntegration(driver, data_formatter)
    
    # Scrape jobs
    all_jobs = []
    try:
        for search_term in JOB_SEARCH_TERMS:
            for location in LOCATIONS:
                logger.info(f"Searching for jobs: '{search_term}' in {location}")
                
                # Get basic job data from search results
                job_results = job_scraper.search_jobs(search_term, location, limit=1)
                logger.info(f"Found {len(job_results)} job results for '{search_term}' in {location}")
                
                # Get detailed information for each job
                detailed_jobs = []
                for job_data in job_results:
                    try:
                        # Get detailed job info
                        detailed_job = job_scraper.get_job_details(job_data)
                        
                        # Generate company URL directly from company name
                        company_name = detailed_job.get("company", "")
                        if company_name:
                            # Generate URL directly from name
                            company_url = company_scraper.url_extractor.generate_url_from_name(company_name)
                            if company_url:
                                detailed_job["company_linkedin_url"] = company_url
                                logger.info(f"Generated company URL from name: {company_url}")
                        
                        # Get company details for the job
                        detailed_job = company_scraper.scrape_company_for_job(detailed_job)
                        
                        # Format job data
                        formatted_job = job_formatter.format_job_data(detailed_job)
                        detailed_jobs.append(formatted_job)
                        all_jobs.append(formatted_job)
                        
                        logger.info(f"Successfully scraped job: {formatted_job['job_title']}")
                        
                        # Add delay between job scrapes
                        time.sleep(random.uniform(1, 3))
                    except Exception as e:
                        logger.error(f"Error processing job: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                # Save jobs for this search term and location
                if detailed_jobs:
                    search_term_filename = f"jobs_{search_term.replace(' ', '_')}_{location.replace(' ', '_')}".lower()
                    job_formatter.save_to_json(
                        detailed_jobs, 
                        search_term_filename
                    )
                
                # Add delay between searches
                time.sleep(random.uniform(3, 5))
        
        # Save all jobs to a single file
        if all_jobs:
            job_formatter.save_to_json(all_jobs, "all_linkedin_jobs")
            logger.info(f"Saved {len(all_jobs)} total jobs to file")
        
    except Exception as e:
        logger.error(f"Error during job scraping: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # Close the browser
        driver.quit()
    
    return True

if __name__ == "__main__":
    main()
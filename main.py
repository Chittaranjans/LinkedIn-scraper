import os
import time
import random
import logging
from dotenv import load_dotenv

# Import from your existing library
from linkedin_scraper import Person, Company

# Import our custom modules
from utils.cookie_auth import LinkedInCookieAuth
from utils.browser_setup import BrowserSetup
from dataformatter.data_formatter import LinkedInFormatter
from linkedin_scraper.custom_company_scraper import CustomCompanyScraper
from utils.logging_config import LoggingConfig

logger = LoggingConfig.setup_logging("linkedin_scraper", "linkedin_scraper.log")


# Load environment variables
load_dotenv()
LINKEDIN_USER = os.getenv('LINKEDIN_USER')
LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD')

# Define target URLs
COMPANY_URLS = [
    "https://www.linkedin.com/company/insight-global/",
    "https://www.linkedin.com/company/microsoft/"
]

PROFILE_URLS = [
    "https://www.linkedin.com/in/satyanadella/",
    "https://www.linkedin.com/in/williamhgates/"
]

class LinkedInScraper:
    def __init__(self):
        self.browser_setup = BrowserSetup()
        self.auth_helper = LinkedInCookieAuth()
        self.formatter = LinkedInFormatter()
        self.driver = None
        
        # Lists for storing scraped data
        self.companies = []
        self.profiles = []
    
    def authenticate(self):
        """Handle LinkedIn authentication with cookies or manual login"""
        # First try without proxy - don't use proxies for login
        logger.info("Starting authentication process")
        
        self.driver = self.browser_setup.create_driver(use_proxy=False)
        if not self.driver:
            logger.error("Failed to create browser")
            return False
        
        # First try cookie-based login
        cookie_login_successful = False
        if os.path.exists('linkedin_cookies.pkl'):
            logger.info("Attempting to login with saved cookies")
            self.auth_helper.load_cookies(self.driver)
            cookie_login_successful = self.auth_helper.verify_login(self.driver)
        
        # If cookie login fails, try manual login
        if not cookie_login_successful:
            logger.info("Cookie login failed, trying manual login")
            return self.auth_helper.get_manual_login(
                self.driver, 
                LINKEDIN_USER, 
                LINKEDIN_PASSWORD
            )
            
        return cookie_login_successful
    
    def scrape_company(self, url):
        """Scrape a company profile with custom implementation"""
        try:
            logger.info(f"Scraping company: {url}")
            
            # Use our custom company scraper instead of the built-in one
            custom_scraper = CustomCompanyScraper(self.driver)
            company_data_dict = custom_scraper.scrape_company(url)
            
            # Format the data
            company_data = self.formatter.format_company_data_from_dict(company_data_dict)
            self.companies.append(company_data)
            
            # Save to file
            company_name = company_data['JobDetails']['companyInfo']['name']
            filename = f"company_{company_name.replace(' ', '_')}"
            self.formatter.save_to_json(company_data, filename)
            
            logger.info(f"Successfully scraped company: {company_name}")
            
            # Add random delay between requests
            time.sleep(random.uniform(3, 6))
            
            return company_data
            
        except Exception as e:
            logger.error(f"Error scraping company {url}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def scrape_profile(self, url):
        """Scrape a person's profile"""
        try:
            logger.info(f"Scraping profile: {url}")
            
            # First navigate to the URL
            self.driver.get(url)
            time.sleep(5)  # Wait for page to load
            
            # Use existing Person scraper
            person = Person(
                linkedin_url=url,
                driver=self.driver,
                close_on_complete=False,
                get=False,  # We already navigated to the URL
                scrape=True
            )
            
            # Format and save data
            profile_data = self.formatter.format_profile_data(person)
            self.profiles.append(profile_data)
            
            # Save to file
            filename = f"profile_{profile_data['name'].replace(' ', '_')}"
            self.formatter.save_to_json(profile_data, filename)
            
            logger.info(f"Successfully scraped profile: {profile_data['name']}")
            
            # Add random delay between requests
            time.sleep(random.uniform(3, 6))
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error scraping profile {url}: {str(e)}")
            return None
    
    def run(self):
        """Run the scraper for all defined URLs"""
        # Authenticate first
        if not self.authenticate():
            logger.error("Authentication failed. Cannot continue.")
            return False
        
        # Scrape companies
        if COMPANY_URLS:
            logger.info("=== SCRAPING COMPANIES ===")
            for url in COMPANY_URLS:
                self.scrape_company(url)
                time.sleep(random.uniform(2, 5))  # Add delay between companies
        
        # Scrape profiles
        if PROFILE_URLS:
            logger.info("=== SCRAPING PROFILES ===")
            for url in PROFILE_URLS:
                self.scrape_profile(url)
                time.sleep(random.uniform(2, 5))  # Add delay between profiles
        
        # Close the browser when done
        if self.driver:
            self.driver.quit()
        
        return True

if __name__ == "__main__":
    # Create and run the scraper
    scraper = LinkedInScraper()
    scraper.run()
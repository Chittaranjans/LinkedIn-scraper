import os
import time
import random
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

# Import our custom modules
from utils.proxy_handler import ProxyHandler
from utils.cookie_auth import LinkedInCookieAuth
from dataformatter.data_formatter import LinkedInFormatter
from linkedin_scraper.custom_company_scraper import CustomCompanyScraper
from utils.logging_config import LoggingConfig

# Setup logging
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
     "https://www.linkedin.com/in/chittaranjan18/",
     "https://www.linkedin.com/in/jsu05/"
]

class LinkedInScraper:
    def __init__(self, proxy_file='utils/proxies.txt', headless=False):
        self.proxy_handler = ProxyHandler(proxy_file=proxy_file)
        self.driver = None
        self.current_proxy = None
        self.headless = headless
        self.company_cache = {}
        self.formatter = LinkedInFormatter()  # Initialize formatter
        self.auth = None  # Will be initialized during setup_driver
        self.setup_driver()
        
    def setup_driver(self):
        """Initialize or refresh the WebDriver with a new proxy"""
        # Close existing driver if any
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        # Create new driver with proxy
        self.driver, self.current_proxy = self.proxy_handler.create_driver(use_proxy=True, headless=self.headless)
        
        if not self.driver:
            # If proxy failed, try without proxy as fallback
            logger.warning("Failed to create driver with proxy. Trying without proxy.")
            self.driver, _ = self.proxy_handler.create_driver(use_proxy=False, headless=self.headless)
            
        if self.driver:
            # Initialize authentication helper
            self.auth = LinkedInCookieAuth(self.driver)

    def authenticate(self):
        """Improved authentication with better error handling"""
        if not self.driver or not self.auth:
            logger.error("Driver or auth not initialized")
            return False
        
        # First try with direct connection (no proxy) for authentication
        original_proxy = self.current_proxy
        original_driver = self.driver
        
        try:
            logger.info("Creating direct connection for authentication")
            self.driver, _ = self.proxy_handler.create_driver(use_proxy=False, headless=self.headless)
            self.auth = LinkedInCookieAuth(self.driver)
            
            # Try cookie authentication
            if os.path.exists(self.auth.cookie_file):
                logger.info("Attempting login with cookies")
                if self.auth.authenticate_with_cookies():
                    logger.info("Successfully authenticated with cookies")
                    
                    # Save the successful driver and quit the old one
                    if original_driver and original_driver != self.driver:
                        try:
                            original_driver.quit()
                        except:
                            pass
                    
                    return True
            
            # If cookie auth fails, try credentials
            if LINKEDIN_USER and LINKEDIN_PASSWORD:
                logger.info("Attempting login with credentials")
                result = self.auth.authenticate_with_credentials(LINKEDIN_USER, LINKEDIN_PASSWORD)
                if result:
                    logger.info("Successfully logged in with credentials")
                    # Save cookies for future use
                    self.auth.save_cookies(driver=self.driver)
                    
                    # Save the successful driver and quit the old one
                    if original_driver and original_driver != self.driver:
                        try:
                            original_driver.quit()
                        except:
                            pass
                        
                    return True
                    
            # If direct connection fails, try with proxy as fallback
            if original_proxy:
                logger.info(f"Trying authentication with original proxy: {original_proxy}")
                self.driver.quit()
                self.driver = original_driver
                self.auth = LinkedInCookieAuth(self.driver)
                
                # Try credentials with proxy
                if LINKEDIN_USER and LINKEDIN_PASSWORD:
                    result = self.auth.authenticate_with_credentials(LINKEDIN_USER, LINKEDIN_PASSWORD)
                    if result:
                        logger.info("Successfully logged in with credentials using proxy")
                        return True
                        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Restore original driver if needed
            if self.driver != original_driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = original_driver
                self.auth = LinkedInCookieAuth(self.driver)
        
        logger.error("All authentication methods failed")
        return False

    def scrape_with_retry(self, url, scrape_function, max_retries=3):
        """Execute a scraping function with retry logic"""
        retries = 0
        while retries < max_retries:
            try:
                logger.info(f"Scraping {url}, attempt {retries+1}/{max_retries}")
                result = scrape_function(url)
                if result:
                    logger.info(f"Successfully scraped {url}")
                    return result
            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
                # Mark current proxy as failed
                if self.current_proxy:
                    logger.info(f"Marking proxy {self.current_proxy} as failed")
                    self.proxy_handler.mark_proxy_as_failed(self.current_proxy)
                
                # Retry with a new proxy
                retries += 1
                if retries < max_retries:
                    logger.info(f"Retrying with new proxy (attempt {retries+1}/{max_retries})")
                    self.setup_driver()  # Get new driver with fresh proxy
                    
                    # Need to authenticate again with new driver
                    if not self.authenticate():
                        logger.error("Authentication failed with new proxy")
                        continue
                        
                    # Random delay between retries
                    delay = random.uniform(2, 5)
                    logger.info(f"Waiting {delay:.1f} seconds before retry")
                    time.sleep(delay)
                else:
                    logger.error(f"Max retries reached for {url}")
        
        return None

    def scrape_company(self, url):
        """Scrape a company profile with retry logic"""
        
        def _do_scrape(url):
            custom_scraper = CustomCompanyScraper(self.driver)
            # Don't include raw data and include employees
            return custom_scraper.scrape_company(url)
        
        # Use retry logic
        company_data = self.scrape_with_retry(url, _do_scrape)
        
        if company_data:
            # Save data to file
            company_name = company_data.get('JobDetails', {}).get('companyInfo', {}).get('name', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"company_{company_name.replace(' ', '_')}_{timestamp}"
            
            # Save to file using formatter
            output_dir = 'scraped_data'
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, f"{filename}.json")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(company_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Company data saved to {filepath}")
            return company_data
            
        return None
        
    def scrape_profile(self, url):
        """Scrape a personal profile with retry logic"""
        
        # Implementation for profile scraping would go here
        logger.warning("Profile scraping not implemented yet")
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
                # Add delay between companies
                delay = random.uniform(3, 8)
                logger.info(f"Waiting {delay:.1f} seconds before next request")
                time.sleep(delay)
        
        # Scrape profiles
        if PROFILE_URLS:
            logger.info("=== SCRAPING PROFILES ===")
            for url in PROFILE_URLS:
                self.scrape_profile(url)
                # Add delay between profiles
                delay = random.uniform(3, 8)
                logger.info(f"Waiting {delay:.1f} seconds before next request")
                time.sleep(delay)
        
        # Close the browser when done
        if self.driver:
            self.driver.quit()
        
        logger.info("Scraping completed")
        return True

if __name__ == "__main__":
    try:
        # Create and run the scraper
        scraper = LinkedInScraper()
        scraper.run()
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        import traceback
        logger.critical(traceback.format_exc())
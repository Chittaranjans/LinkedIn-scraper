import os
import time
import random
import logging
import traceback
from selenium.common.exceptions import TimeoutException, WebDriverException
from dotenv import load_dotenv

# Import from your existing library
from linkedin_scraper import Person, Company, actions

# Import our custom modules
from utils.proxy_handler import ProxyHandler
from dataformatter.data_formatter import LinkedInFormatter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("linkedin_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("linkedin_scraper_main")

# Load environment variables
load_dotenv()
LINKEDIN_USER = os.getenv('LINKEDIN_USER')
LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD')

class LinkedInScraper:
    def __init__(self):
        self.proxy_handler = ProxyHandler()
        self.formatter = LinkedInFormatter()
        self.driver = None
        self.current_proxy = None
        self.login_successful = False
        
        # Configure some wait times
        self.page_load_wait = 5
        self.action_wait = 2
        
        # Initialize an empty list of scraped items
        self.scraped_companies = []
        self.scraped_profiles = []
    
    def initialize_driver(self, use_proxy=True):
        """Initialize WebDriver with optional proxy"""
        logger.info("Initializing WebDriver...")
        
        # Close existing driver if one exists
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        # Create a new driver with or without proxy
        self.driver, self.current_proxy = self.proxy_handler.create_driver(use_proxy=use_proxy)
        
        if not self.driver:
            logger.error("Failed to initialize WebDriver")
            return False
            
        return True
    
    def login(self, max_attempts=3):
        """Login to LinkedIn with retry mechanism"""
        if not LINKEDIN_USER or not LINKEDIN_PASSWORD:
            logger.error("LinkedIn credentials missing in .env file")
            return False
            
        logger.info(f"Attempting to login to LinkedIn as {LINKEDIN_USER}")
        
        # Try logging in with different approaches
        for attempt in range(max_attempts):
            try:
                logger.info(f"Login attempt {attempt+1}/{max_attempts}")
                
                # Navigate to LinkedIn login page
                self.driver.get("https://www.linkedin.com/login")
                time.sleep(self.page_load_wait)
                
                # Use your existing actions.login function
                actions.login(self.driver, email=LINKEDIN_USER, password=LINKEDIN_PASSWORD)
                
                # Wait for login to complete
                time.sleep(self.page_load_wait)
                
                # Verify login success by checking URL
                current_url = self.driver.current_url
                if "feed" in current_url or "mynetwork" in current_url:
                    logger.info("Login successful!")
                    self.login_successful = True
                    return True
                else:
                    logger.warning(f"Login may have failed. Current URL: {current_url}")
                    
                    # Check if there's a security challenge
                    if "checkpoint" in current_url or "challenge" in current_url:
                        logger.error("LinkedIn security verification detected")
                        
                        # Try a direct connection on last attempt
                        if attempt == max_attempts - 1:
                            logger.info("Trying final login with direct connection")
                            if self.current_proxy:
                                # Mark this proxy as failed
                                self.proxy_handler.mark_proxy_as_failed(self.current_proxy)
                                
                            # Create a new driver without proxy
                            self.initialize_driver(use_proxy=False)
                            self.driver.get("https://www.linkedin.com/login")
                            time.sleep(self.page_load_wait)
                            actions.login(self.driver, email=LINKEDIN_USER, password=LINKEDIN_PASSWORD)
                            time.sleep(self.page_load_wait)
                            
                            if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                                logger.info("Login with direct connection successful!")
                                self.login_successful = True
                                return True
                
            except TimeoutException:
                logger.warning("Timeout during login")
                
            except WebDriverException as e:
                logger.warning(f"WebDriver error during login: {str(e)}")
                
            except Exception as e:
                logger.error(f"Unexpected error during login: {str(e)}")
                logger.error(traceback.format_exc())
                
            # If we reach here, login failed for this attempt
            
            # Mark current proxy as failed
            if self.current_proxy:
                self.proxy_handler.mark_proxy_as_failed(self.current_proxy)
                
            # Try again with a new proxy
            if attempt < max_attempts - 1:
                logger.info("Retrying with a new proxy")
                self.initialize_driver(use_proxy=True)
                
        # If we reach here, all login attempts failed
        logger.error("Failed to login after all attempts")
        return False
    
    def scrape_company(self, url, retry_count=0, max_retries=2):
        """Scrape company data from LinkedIn"""
        if not self.login_successful:
            logger.error("Not logged in. Cannot scrape company")
            return None
            
        logger.info(f"Scraping company: {url}")
        
        try:
            # Use your existing Company class to scrape
            company = Company(
                linkedin_url=url,
                driver=self.driver,
                close_on_complete=False,
                get_employees=True
            )
            
            # Add random wait to avoid detection
            time.sleep(random.uniform(self.action_wait, self.action_wait * 2))
            
            # Format the data
            company_data = self.formatter.format_company_data(company)
            
            # Save the data
            self.formatter.save_to_json(company_data, f"company_{company_data['JobDetails']['companyInfo']['name'].replace(' ', '_')}")
            
            # Add to our list of scraped companies
            self.scraped_companies.append(company_data)
            
            logger.info(f"Successfully scraped company: {company_data['JobDetails']['companyInfo']['name']}")
            return company_data
            
        except TimeoutException as e:
            logger.error(f"Timeout error scraping company {url}: {str(e)}")
            
        except WebDriverException as e:
            logger.error(f"WebDriver error scraping company {url}: {str(e)}")
            
            # Mark the current proxy as failed
            if self.current_proxy:
                self.proxy_handler.mark_proxy_as_failed(self.current_proxy)
                
        except Exception as e:
            logger.error(f"Unexpected error scraping company {url}: {str(e)}")
            logger.error(traceback.format_exc())
            
        # Retry logic
        if retry_count < max_retries:
            logger.info(f"Retrying company {url} (attempt {retry_count+1}/{max_retries})")
            
            # Get a new driver with a fresh proxy
            self.initialize_driver()
            
            # Need to login again with the new driver
            if self.login():
                return self.scrape_company(url, retry_count + 1, max_retries)
            
        return None
    
    def scrape_profile(self, url, retry_count=0, max_retries=2):
        """Scrape profile data from LinkedIn"""
        if not self.login_successful:
            logger.error("Not logged in. Cannot scrape profile")
            return None
            
        logger.info(f"Scraping profile: {url}")
        
        try:
            # Use your existing Person class to scrape
            person = Person(
                linkedin_url=url,
                driver=self.driver,
                close_on_complete=False,
                scrape=True
            )
            
            # Add random wait to avoid detection
            time.sleep(random.uniform(self.action_wait, self.action_wait * 2))
            
            # Format the data
            profile_data = self.formatter.format_profile_data(person)
            
            # Save the data
            self.formatter.save_to_json(profile_data, f"profile_{profile_data['name'].replace(' ', '_')}")
            
            # Add to our list of scraped profiles
            self.scraped_profiles.append(profile_data)
            
            logger.info(f"Successfully scraped profile: {profile_data['name']}")
            return profile_data
            
        except TimeoutException as e:
            logger.error(f"Timeout error scraping profile {url}: {str(e)}")
            
        except WebDriverException as e:
            logger.error(f"WebDriver error scraping profile {url}: {str(e)}")
            
            # Mark the current proxy as failed
            if self.current_proxy:
                self.proxy_handler.mark_proxy_as_failed(self.current_proxy)
                
        except Exception as e:
            logger.error(f"Unexpected error scraping profile {url}: {str(e)}")
            logger.error(traceback.format_exc())
            
        # Retry logic
        if retry_count < max_retries:
            logger.info(f"Retrying profile {url} (attempt {retry_count+1}/{max_retries})")
            
            # Get a new driver with a fresh proxy
            self.initialize_driver()
            
            # Need to login again with the new driver
            if self.login():
                return self.scrape_profile(url, retry_count + 1, max_retries)
            
        return None
    
    def save_all_results(self):
        """Save all scraped data to JSON files"""
        if self.scraped_companies:
            self.formatter.save_to_json(self.scraped_companies, "all_companies")
            
        if self.scraped_profiles:
            self.formatter.save_to_json(self.scraped_profiles, "all_profiles")
    
    def run_scraper(self, company_urls=None, profile_urls=None):
        """Run the scraper for specified URLs"""
        # Set default empty lists if none provided
        company_urls = company_urls or []
        profile_urls = profile_urls or []
        
        # Initialize the driver
        if not self.initialize_driver():
            logger.error("Failed to initialize WebDriver")
            return False
            
        # Login to LinkedIn
        if not self.login():
            logger.error("Failed to login to LinkedIn")
            return False
            
        # Scrape companies
        if company_urls:
            logger.info("=== SCRAPING COMPANIES ===")
            for url in company_urls:
                company_data = self.scrape_company(url)
                # Add wait between requests
                time.sleep(random.uniform(3, 6))
                
                # Check if we need a new proxy
                if not company_data and self.current_proxy:
                    logger.info("Switching to a new proxy")
                    self.initialize_driver()
                    self.login()
        
        # Scrape profiles
        if profile_urls:
            logger.info("=== SCRAPING PROFILES ===")
            for url in profile_urls:
                profile_data = self.scrape_profile(url)
                # Add wait between requests
                time.sleep(random.uniform(3, 6))
                
                # Check if we need a new proxy
                if not profile_data and self.current_proxy:
                    logger.info("Switching to a new proxy")
                    self.initialize_driver()
                    self.login()
        
        # Save all results
        self.save_all_results()
        
        # Close the driver
        if self.driver:
            self.driver.quit()
            
        return True
import time
import logging
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from utils.logging_config import LoggingConfig

# Set up logging
logger = LoggingConfig.setup_logging("company_url_extractor")

class CompanyUrlExtractor:
    def __init__(self, driver):
        self.driver = driver
    
    def generate_url_from_name(self, company_name):
        """Generate a LinkedIn company URL from company name"""
        if not company_name:
            return None
            
        # Clean company name - remove Ltd, LLC, Inc, etc.
        clean_name = re.sub(r'\s+(?:Ltd|LLC|Inc|Corp|Limited|Corporation|Company|Technologies|Services|Solutions)\.?$', '', company_name, flags=re.IGNORECASE)
        
        # Replace spaces with hyphens and convert to lowercase
        url_name = clean_name.lower().strip()
        url_name = re.sub(r'\s+', '-', url_name)  # Replace spaces with hyphens
        url_name = re.sub(r'[^\w\-]', '', url_name)  # Remove special chars except hyphens
        
        # Build URL
        company_url = f"https://www.linkedin.com/company/{url_name}/"
        logger.info(f"Generated company URL: {company_url} from name: {company_name}")
        
        return company_url
    
    def extract_company_url_from_job(self, job_url):
        """Extract company URL from a job listing page"""
        logger.info(f"Extracting company URL from job page: {job_url}")
        
        try:
            # Navigate to the job page
            current_url = self.driver.current_url
            if current_url != job_url:
                self.driver.get(job_url)
                time.sleep(3)
            
            # First get the company name, which we'll need if direct extraction fails
            company_name = None
            for selector in [".jobs-unified-top-card__company-name", ".job-details-jobs-unified-top-card__company-name"]:
                try:
                    company_name_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    company_name = company_name_elem.text.strip()
                    if company_name:
                        break
                except NoSuchElementException:
                    pass
            
            # Try multiple approaches to find the company link
            company_url = None
            
            # Method 1: Direct company name link
            try:
                company_link = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-unified-top-card__company-name a"))
                )
                company_url = company_link.get_attribute("href")
                logger.info(f"Found company URL (method 1): {company_url}")
            except (TimeoutException, NoSuchElementException):
                pass
            
            # Method 2: Alternative selector
            if not company_url:
                try:
                    company_link = self.driver.find_element(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__company-name a")
                    company_url = company_link.get_attribute("href")
                    logger.info(f"Found company URL (method 2): {company_url}")
                except NoSuchElementException:
                    pass
            
            # Method 3: Try clicking on company name to see if it's a link
            if not company_url:
                try:
                    # Find any element that looks like a company name
                    company_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                        ".jobs-unified-top-card__company-name, " + 
                        ".job-details-jobs-unified-top-card__company-name, " +
                        ".jobs-company__name, " +
                        "a[data-tracking-control-name='public_jobs_topcard-org-name']"
                    )
                    
                    if company_elements:
                        # Try to click the element (it might be a link)
                        for element in company_elements:
                            try:
                                current_url = self.driver.current_url
                                element.click()
                                time.sleep(2)
                                
                                # If URL changed, we likely got to the company page
                                if self.driver.current_url != current_url:
                                    company_url = self.driver.current_url
                                    logger.info(f"Found company URL by clicking (method 3): {company_url}")
                                    
                                    # Go back to job page
                                    self.driver.back()
                                    time.sleep(2)
                                    break
                            except:
                                continue
                except Exception as e:
                    logger.debug(f"Error in method 3: {str(e)}")
            
            # Method 4: Extract from HTML source
            if not company_url:
                try:
                    html_source = self.driver.page_source
                    # Look for company URLs in the page source
                    company_patterns = [
                        r'href="(https://www\.linkedin\.com/company/[^"]+)"',
                        r'"companyPageUrl":"(https:\\\/\\\/www\.linkedin\.com\\\/company\\\/[^"]+)"',
                        r'"companyUrn":"([^"]+)"'
                    ]
                    
                    for pattern in company_patterns:
                        matches = re.findall(pattern, html_source)
                        if matches:
                            # Take first match
                            raw_url = matches[0]
                            # Clean up any escaped characters
                            company_url = raw_url.replace('\\/', '/')
                            logger.info(f"Found company URL from HTML source (method 4): {company_url}")
                            break
                except Exception as e:
                    logger.debug(f"Error in method 4: {str(e)}")
            
            # Method 5: Generate URL from company name as a last resort
            if not company_url and company_name:
                company_url = self.generate_url_from_name(company_name)
                logger.info(f"Generated company URL from name (method 5): {company_url}")
            
            # Clean up the URL if found
            if company_url:
                # Remove any parameters or fragments
                company_url = company_url.split('?')[0].split('#')[0]
                
                # Make sure it's a company URL
                if '/company/' in company_url:
                    # Ensure it ends with a slash
                    if not company_url.endswith('/'):
                        company_url += '/'
                    return company_url
                else:
                    logger.warning(f"URL doesn't look like a company URL: {company_url}")
            
            if company_name:
                # If all else fails, try one more time with the company name
                return self.generate_url_from_name(company_name)
            
            logger.warning("Could not find or generate company URL")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting company URL: {str(e)}")
            return None

    def get_company_name_from_job_page(self, job_url):
        """Extract just the company name from a job listing page"""
        logger.info(f"Extracting company name from job page: {job_url}")
        
        try:
            # Navigate to the job page if needed
            current_url = self.driver.current_url
            if current_url != job_url:
                self.driver.get(job_url)
                time.sleep(2)
            
            # Extract company name using multiple selectors
            company_name = None
            
            # Try various selectors to find the company name
            selectors = [
                ".jobs-unified-top-card__company-name",
                ".job-details-jobs-unified-top-card__company-name",
                ".jobs-company__name",
                "[data-tracking-control-name='public_jobs_topcard-org-name']"
            ]
            
            for selector in selectors:
                try:
                    company_name_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    company_name = company_name_elem.text.strip()
                    if company_name:
                        logger.info(f"Found company name: {company_name}")
                        break
                except NoSuchElementException:
                    continue
            
            return company_name
            
        except Exception as e:
            logger.error(f"Error extracting company name: {str(e)}")
            return None
    
    def get_company_url_for_job(self, job_data):
        """Get company URL for a job using name-based generation"""
        company_name = job_data.get('company')
        
        # If no company name in job data, try to extract from job URL
        if not company_name and job_data.get('linkedin_url'):
            company_name = self.get_company_name_from_job_page(job_data['linkedin_url'])
        
        if company_name:
            return self.generate_url_from_name(company_name)
        else:
            logger.warning("No company name found, cannot generate URL")
            return None
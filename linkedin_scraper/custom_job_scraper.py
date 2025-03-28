import logging
import time
import random
import re
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from linkedin_scraper.company_url_extractor import CompanyUrlExtractor
from utils.logging_config import LoggingConfig

logger = LoggingConfig.setup_logging("custom_job_scraper")


class CustomJobScraper:
    def __init__(self, driver):
        self.driver = driver
        self.wait_short = WebDriverWait(self.driver, 5)
        self.wait_medium = WebDriverWait(self.driver, 10)
        self.wait_long = WebDriverWait(self.driver, 20)
        self.url_extractor = CompanyUrlExtractor(driver)
    
    def get_text_safely(self, selector, method=By.CSS_SELECTOR, wait_time=5, default=""):
        """Get text from an element safely with a fallback value"""
        try:
            element = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((method, selector))
            )
            return element.text.strip()
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            return default
    
    def get_attribute_safely(self, selector, attribute, method=By.CSS_SELECTOR, wait_time=5, default=""):
        """Get an attribute from an element safely with a fallback value"""
        try:
            element = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((method, selector))
            )
            return element.get_attribute(attribute) or default
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            return default
    
    def scroll_page(self, amount=800):
        """Scroll the page by given amount"""
        self.driver.execute_script(f"window.scrollBy(0, {amount});")
        time.sleep(random.uniform(0.5, 1.5))
    
    def search_jobs(self, search_term, location=None, limit=10):
        """Search for jobs and return basic job data"""
        logger.info(f"Searching for jobs with term: '{search_term}'")
        
        # Build search URL
        base_url = "https://www.linkedin.com/jobs/search/"
        query_params = f"?keywords={search_term}"
        if location:
            query_params += f"&location={location}"
        query_params += "&f_TPR=r86400" # Last 24 hours
        
        # Navigate to search page
        self.driver.get(base_url + query_params)
        time.sleep(3)
        
        # Find job listing container - try multiple selectors
        job_list_selectors = [
            ".jobs-search-results-list", 
            ".jobs-search__results-list",
            "div[data-tracking-control-name='job-search-results']",
            ".scaffold-layout__list"
        ]
        
        job_list = None
        for selector in job_list_selectors:
            try:
                job_list = self.wait_medium.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                logger.info(f"Found job list container with selector: {selector}")
                break
            except TimeoutException:
                continue
        
        if not job_list:
            # Try to find any job cards without the container
            logger.warning("Couldn't find job list container, looking for job cards directly")
            try:
                # Scroll a few times to load content
                for _ in range(3):
                    self.scroll_page()
            except:
                pass
        
        # Find job cards - try multiple selectors
        job_card_selectors = [
            ".job-search-card",
            ".jobs-search-results__list-item",
            "ul.jobs-search-results__list > li",
            "div[data-job-id]"
        ]
        
        job_cards = []
        for selector in job_card_selectors:
            try:
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if job_cards:
                    logger.info(f"Found {len(job_cards)} job cards with selector: {selector}")
                    break
            except:
                continue
        
        if not job_cards:
            logger.error("Could not find any job cards on the page")
            return []
        
        # Process job cards (limited to specified number)
        jobs_to_process = min(len(job_cards), limit)
        job_results = []
        
        for i in range(jobs_to_process):
            try:
                # Re-fetch element to avoid stale references
                job_card = job_cards[i]
                
                # Extract basic job data
                job_data = self._extract_job_card_data(job_card)
                if job_data:
                    job_results.append(job_data)
                    logger.info(f"Extracted basic data for job: {job_data.get('job_title')} at {job_data.get('company')}")
                    
                # Don't process too quickly
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                logger.error(f"Error processing job card {i}: {str(e)}")
        
        return job_results
    
    def _extract_job_card_data(self, job_card):
        """Extract data from a job card"""
        try:
            # Try multiple approaches to get job title
            job_title = None
            for selector in ['h3.base-search-card__title', '.job-card-list__title', '.job-card-container__link', 'h3', '.artdeco-entity-lockup__title']:
                try:
                    title_elem = job_card.find_element(By.CSS_SELECTOR, selector)
                    job_title = title_elem.text.strip()
                    if job_title:
                        break
                except:
                    continue
            
            # Try multiple approaches to get company name
            company = None
            for selector in ['.base-search-card__subtitle', '.job-card-container__company-name', '.artdeco-entity-lockup__subtitle']:
                try:
                    company_elem = job_card.find_element(By.CSS_SELECTOR, selector)
                    company = company_elem.text.strip()
                    if company:
                        break
                except:
                    continue
            
            # Try multiple approaches to get location
            location = None
            for selector in ['.job-card-container__metadata-item', '.job-search-card__location', '.artdeco-entity-lockup__caption']:
                try:
                    location_elem = job_card.find_element(By.CSS_SELECTOR, selector)
                    location = location_elem.text.strip()
                    if location:
                        break
                except:
                    continue
            
            # Try to get job URL
            job_url = None
            try:
                anchor = job_card.find_element(By.TAG_NAME, 'a')
                job_url = anchor.get_attribute('href')
                # Clean up URL
                if job_url and '?' in job_url:
                    job_url = job_url.split('?')[0]
            except:
                # Try other approaches
                try:
                    # Get data-entity-urn attribute which contains the job ID
                    job_id = job_card.get_attribute('data-job-id') or job_card.get_attribute('data-entity-urn')
                    if job_id:
                        if 'jobPosting:' in job_id:
                            job_id = job_id.split('jobPosting:')[1]
                        job_url = f"https://www.linkedin.com/jobs/view/{job_id}"
                except:
                    pass
            
            # Create job data object
            if job_title and company:
                return {
                    "job_title": job_title,
                    "company": company,
                    "location": location or "",
                    "linkedin_url": job_url or "",
                    "posted_date": "",
                    "applicant_count": "",
                    "job_description": "",
                    "benefits": ""
                }
            else:
                return None
            
        except Exception as e:
            logger.error(f"Error extracting job card data: {str(e)}")
            return None
    
    def get_job_details(self, job_data):
        """Get detailed information for a job by navigating to its page"""
        if not job_data or not job_data.get("linkedin_url"):
            logger.error("Missing job URL, cannot fetch details")
            return job_data
        
        try:
            job_url = job_data["linkedin_url"]
            logger.info(f"Getting details for job: {job_data['job_title']} at {job_data['company']}")
            
            # Navigate to job page
            self.driver.get(job_url)
            time.sleep(3)
            
            # Extract detailed information
            try:
                # Get posted date - try multiple approaches
                posted_date = self.get_text_safely(".jobs-unified-top-card__posted-date") or \
                              self.get_text_safely(".jobs-details-job-summary__text--expander") or \
                              self.get_text_safely('[data-test-job-insight-timestamp]')
                
                # Clean up posted date
                if posted_date:
                    # Extract just the date part if there's extra text
                    date_match = re.search(r'(Posted|posted)?\s*(\d+[a-zA-Z\s,]+ago|\d+/\d+/\d+|today|yesterday)', posted_date, re.IGNORECASE)
                    if date_match:
                        posted_date = date_match.group(2).strip()
                
                job_data["posted_date"] = posted_date
                
                # Get applicant count
                applicant_count = self.get_text_safely(".jobs-unified-top-card__applicant-count") or \
                                 self.get_text_safely(".jobs-top-card__applicant-count") or \
                                 self.get_text_safely('[data-test-applicants-count]')
                job_data["applicant_count"] = applicant_count.strip() if applicant_count else ""
                
                # Get job description
                job_description = self.get_text_safely(".jobs-description") or \
                                 self.get_text_safely(".jobs-description-content") or \
                                 self.get_text_safely('[data-test-job-description]')
                job_data["job_description"] = job_description
                
                # Get benefits/salary info if available
                benefits = self.get_text_safely(".jobs-unified-top-card__job-insight") or \
                          self.get_text_safely(".jobs-salary-header__container")
                job_data["benefits"] = benefits if benefits else ""
                
                # Extract job requirements and skills
                if job_description:
                    skills_data = self.extract_skills_and_requirements(job_description)
                    job_data["requirements"] = skills_data["all_requirements"]
                    job_data["technical_skills"] = skills_data["technical_skills"]
                else:
                    job_data["requirements"] = []
                    job_data["technical_skills"] = []
                
                # Get company LinkedIn URL if not already present
                if not job_data.get("company_linkedin_url") or not job_data.get("company_linkedin_url").strip():
                    # Try to extract from page
                    company_url = self.url_extractor.extract_company_url_from_job(job_url)
                    if company_url:
                        job_data["company_linkedin_url"] = company_url
                        logger.info(f"Found company URL: {company_url}")
                    else:
                        # Fall back to generating from company name
                        company_name = job_data.get("company")
                        if company_name:
                            company_url = self.url_extractor.generate_url_from_name(company_name)
                            if company_url:
                                job_data["company_linkedin_url"] = company_url
                                logger.info(f"Generated company URL from name: {company_url}")
                
                logger.info(f"Successfully scraped details for job: {job_data['job_title']}")
                
            except Exception as e:
                logger.error(f"Error extracting job details: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error navigating to job page: {str(e)}")
        
        return job_data

    def extract_skills_and_requirements(self, job_description):
        """Extract skills and requirements from job description"""
        # Initialize empty list for skills
        skills = []
        
        # Look for common requirement section indicators
        requirement_sections = []
        
        # Try to find requirements section by common headers
        patterns = [
            r"(?:requirements|qualifications|what you.*need|what we.*looking for|skills|expertise|experience required)(?:\s*:|\s*\n)",
            r"(?:you have|you've got|you will have|you'll have|you should have|you must have)(?:\s*:|\s*\n)",
            r"(?:required skills|technical skills|minimum qualifications|basic qualifications|key qualifications)(?:\s*:|\s*\n)",
        ]
        
        # Find all potential requirement sections
        job_desc_lower = job_description.lower()
        for pattern in patterns:
            matches = re.finditer(pattern, job_desc_lower, re.IGNORECASE)
            for match in matches:
                start_pos = match.end()
                # Look for the next section header or end of text
                next_section = re.search(r"\n\s*(?:[A-Z][A-Za-z\s]+:|\n\n)", job_description[start_pos:])
                end_pos = start_pos + next_section.start() if next_section else len(job_description)
                requirement_text = job_description[start_pos:end_pos].strip()
                requirement_sections.append(requirement_text)
        
        # If we couldn't find specific sections, use the whole description
        if not requirement_sections and len(job_description) > 0:
            requirement_sections = [job_description]
        
        # Process each requirements section to extract skills
        for section in requirement_sections:
            # Extract bullet points (common format for requirements)
            bullet_points = re.findall(r'(?:^|\n)(?:[\s•\-\*\+◦▪️⦿⚫⚬○●■□»]|[0-9]+\.)\s*([^\n]+)', section)
            
            # If no bullet points found, try to split by newlines
            if not bullet_points:
                bullet_points = [line.strip() for line in section.split('\n') if line.strip()]
            
            # Extract skills from bullet points
            for point in bullet_points:
                # Clean up the point
                point = point.strip()
                if len(point) > 5:  # Skip very short items
                    skills.append(point)
        
        # Extract technical skills like programming languages, tools, frameworks
        tech_skills = []
        tech_patterns = [
            r'\b(?:Java|Python|JavaScript|JS|TypeScript|TS|Ruby|PHP|Go|Golang|Rust|C\+\+|C#|Swift)\b',
            r'\b(?:React|Angular|Vue|Node\.js|Django|Flask|Spring|Rails|Express\.js|Next\.js|Laravel)\b',
            r'\b(?:SQL|NoSQL|MySQL|PostgreSQL|MongoDB|Oracle|DynamoDB|Cassandra|Redis)\b',
            r'\b(?:AWS|Azure|GCP|Docker|Kubernetes|CI/CD|Git|Jenkins|Terraform|Ansible)\b',
            r'\b(?:Machine Learning|AI|Deep Learning|NLP|Computer Vision|Data Science)\b',
            r'\b(?:Agile|Scrum|Kanban|JIRA|Confluence|DevOps|SRE)\b'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, job_description)
            tech_skills.extend(matches)
        
        # Remove duplicates and sort
        tech_skills = sorted(list(set(tech_skills)))
        
        return {
            "all_requirements": skills,
            "technical_skills": tech_skills
        }
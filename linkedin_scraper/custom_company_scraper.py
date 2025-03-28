import logging
import time
import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.logging_config import LoggingConfig

# Set up logging
logger = LoggingConfig.setup_logging("custom_company_scraper")

class CustomCompanyScraper:
    def __init__(self, driver):
        self.driver = driver
        
    def get_text_safely(self, selector, method=By.CSS_SELECTOR, wait_time=5, default=""):
        """Get text from an element safely with a fallback value"""
        try:
            element = self.driver.find_element(method, selector)
            return element.text.strip()
        except NoSuchElementException:
            return default
    
    def get_attribute_safely(self, selector, attribute, method=By.CSS_SELECTOR, wait_time=5, default=""):
        """Get an attribute from an element safely with a fallback value"""
        try:
            element = self.driver.find_element(method, selector)
            return element.get_attribute(attribute) or default
        except NoSuchElementException:
            return default
    
    def scroll_down(self, amount=800):
        """Scroll down the page by given amount"""
        self.driver.execute_script(f"window.scrollBy(0, {amount});")
        time.sleep(1)
    
    def is_year(self, text):
        """Check if text is a year (1900-2030)"""
        if not text:
            return False
        return bool(re.match(r'^(19\d{2}|20[0-3]\d)$', text.strip()))
    
    def is_location(self, text):
        """Check if text looks like a location (contains comma or common location terms)"""
        if not text:
            return False
        if ',' in text:
            return True
        location_terms = ['street', 'avenue', 'road', 'blvd', 'city', 'town', 'state', 'county', 'district']
        return any(term in text.lower() for term in location_terms)
    
    def is_company_size(self, text):
        """Check if text describes company size"""
        if not text:
            return False
        size_patterns = [
            r'employees', r'staff', r'personnel',
            r'1-\d+', r'\d+-\d+', r'\d+,\d+', r'\d+\+'
        ]
        return any(re.search(pattern, text.lower()) for pattern in size_patterns)
    
    def is_specialties(self, text):
        """Check if text contains multiple comma-separated items (likely specialties)"""
        # Specialties typically have multiple comma-separated terms
        return text and text.count(',') >= 2 and not self.is_location(text)
    
    def has_associated_members(self, text):
        """Check if text contains 'associated members'"""
        return text and 'associated members' in text.lower()

    def get_leadership_profiles(self, company_url, max_leaders=5):
        """Get leadership profiles from the company page"""
        leadership = []
        try:
            # Navigate to the people page with leadership filter
            people_url = f"{company_url}people/?keywords=CEO%20OR%20founder%20OR%20president%20OR%20director%20OR%20executive"
            self.driver.get(people_url)
            time.sleep(3)
            
            # Try to find leadership filter button if exists
            try:
                filter_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".artdeco-pill.artdeco-pill--slate.artdeco-pill--choice.artdeco-pill--2.search-reusables__filter-pill-button")
                for button in filter_buttons:
                    if "Leaders" in button.text:
                        button.click()
                        time.sleep(2)
                        break
            except:
                # If no filter buttons exist, continue with the search results
                pass
                
            # Scroll to load more content
            for _ in range(3):
                self.scroll_down()
            
            # Try different selectors for employee cards
            employee_cards = self.driver.find_elements(By.CSS_SELECTOR, ".org-people-profile-card") or \
                           self.driver.find_elements(By.CSS_SELECTOR, ".discover-person-card") or \
                           self.driver.find_elements(By.CSS_SELECTOR, ".org-people-profiles-card") or \
                           self.driver.find_elements(By.CSS_SELECTOR, ".artdeco-entity-lockup")
            
            for i, card in enumerate(employee_cards):
                if i >= max_leaders:  # Limit to specified number of leaders
                    break
                
                try:
                    # Extract person name
                    name = ""
                    for selector in ['.org-people-profile-card__profile-title', '.discover-person-card__name', 
                                    '.artdeco-entity-lockup__title', '.org-people-profile-card__profile-info']:
                        try:
                            name_elem = card.find_element(By.CSS_SELECTOR, selector)
                            name = name_elem.text.strip()
                            if name:
                                break
                        except NoSuchElementException:
                            continue
                    
                    if not name:
                        name = "Unknown"
                    
                    # Extract position/title
                    position = ""
                    for selector in ['.artdeco-entity-lockup__subtitle', '.discover-person-card__occupation', 
                                    '.org-people-profile-card__subtitle', '.t-14.t-black--light.t-normal']:
                        try:
                            position_elem = card.find_element(By.CSS_SELECTOR, selector)
                            position = position_elem.text.strip()
                            if position:
                                break
                        except NoSuchElementException:
                            continue
                    
                    # Extract LinkedIn URL
                    profile_url = ""
                    try:
                        anchor = card.find_element(By.TAG_NAME, "a")
                        profile_url = anchor.get_attribute("href")
                        
                        # Clean up URL (remove query params)
                        if profile_url and '?' in profile_url:
                            profile_url = profile_url.split('?')[0]
                    except:
                        pass
                    
                    # Extract photo URL
                    photo_url = ""
                    try:
                        img = card.find_element(By.TAG_NAME, "img")
                        photo_url = img.get_attribute("src")
                    except:
                        pass
                    
                    # Add to leadership list
                    if name and position:
                        leadership.append({
                            "name": name,
                            "position": position,
                            "url": profile_url,
                            "photo_url": photo_url
                        })
                except Exception as e:
                    logger.debug(f"Error processing leadership profile: {str(e)}")
            
            logger.info(f"Found {len(leadership)} leadership profiles")
            
        except Exception as e:
            logger.error(f"Error getting leadership profiles: {str(e)}")
        
        return leadership
    
    def get_regular_employees(self, company_url, max_employees=10):
        """Get regular employees from the company page (not just leadership)"""
        employees = []
        try:
            # Navigate to the people page without leadership filter
            people_url = f"{company_url}people/"
            self.driver.get(people_url)
            time.sleep(3)
            
            # Scroll to load more content
            for _ in range(3):
                self.scroll_down()
            
            # Try different selectors for employee cards
            employee_cards = self.driver.find_elements(By.CSS_SELECTOR, ".org-people-profile-card") or \
                           self.driver.find_elements(By.CSS_SELECTOR, ".discover-person-card") or \
                           self.driver.find_elements(By.CSS_SELECTOR, ".org-people-profiles-card") or \
                           self.driver.find_elements(By.CSS_SELECTOR, ".artdeco-entity-lockup")
            
            # Process each employee card
            for i, card in enumerate(employee_cards):
                if i >= max_employees:  # Limit to specified number of employees
                    break
                
                try:
                    # Extract person name
                    name = ""
                    for selector in ['.org-people-profile-card__profile-title', '.discover-person-card__name', 
                                    '.artdeco-entity-lockup__title', '.org-people-profile-card__profile-info']:
                        try:
                            name_elem = card.find_element(By.CSS_SELECTOR, selector)
                            name = name_elem.text.strip()
                            if name:
                                break
                        except NoSuchElementException:
                            continue
                
                    if not name:
                        name = "Unknown"
                
                    # Extract position/title
                    position = ""
                    for selector in ['.artdeco-entity-lockup__subtitle', '.discover-person-card__occupation', 
                                    '.org-people-profile-card__subtitle', '.t-14.t-black--light.t-normal']:
                        try:
                            position_elem = card.find_element(By.CSS_SELECTOR, selector)
                            position = position_elem.text.strip()
                            if position:
                                break
                        except NoSuchElementException:
                            continue
                
                    # Extract LinkedIn URL
                    profile_url = ""
                    try:
                        anchor = card.find_element(By.TAG_NAME, "a")
                        profile_url = anchor.get_attribute("href")
                        
                        # Clean up URL (remove query params)
                        if profile_url and '?' in profile_url:
                            profile_url = profile_url.split('?')[0]
                    except:
                        pass
                
                    # Extract photo URL
                    photo_url = ""
                    try:
                        img = card.find_element(By.TAG_NAME, "img")
                        photo_url = img.get_attribute("src")
                    except:
                        pass
                
                    # Add to employees list
                    if name and (position or profile_url):
                        employees.append({
                            "name": name,
                            "position": position,
                            "url": profile_url,
                            "photo_url": photo_url
                        })
                except Exception as e:
                    logger.debug(f"Error processing employee profile: {str(e)}")
        
            logger.info(f"Found {len(employees)} employee profiles")
        
        except Exception as e:
            logger.error(f"Error getting employee profiles: {str(e)}")
    
        return employees

    def scrape_company(self, url):
        """Scrape LinkedIn company page with robust selectors"""
        logger.info(f"Scraping company page using custom scraper: {url}")
        
        # Navigate to the URL
        self.driver.get(url)
        time.sleep(5)  # Wait for page to load
        
        # Scroll down multiple times to load more content
        for _ in range(3):
            self.scroll_down()
        
        # Company name - try multiple selectors
        company_name = self.get_text_safely(".org-top-card-summary__title") or \
                       self.get_text_safely("h1.t-24.t-black.t-bold") or \
                       self.get_text_safely("h1.ember-view", method=By.CSS_SELECTOR) or \
                       "Unknown Company"
        
        logger.info(f"Found company name: {company_name}")
        
        # Website URL - try multiple approaches
        website = self.get_attribute_safely(".org-top-card__primary-actions a", "href") or \
                  self.get_attribute_safely("a.ember-view.org-top-card-primary-actions__action", "href")
        
        # Enhanced logo extraction
        logo_url = ""
        try:
            # Try multiple selectors for company logo
            for logo_selector in [
                ".org-top-card-primary-content__logo img",
                ".org-top-card__logo img", 
                ".org-organization-page__logo img",
                ".artdeco-entity-image",
                ".org-company-card__logo img"
            ]:
                try:
                    logo_elem = self.driver.find_element(By.CSS_SELECTOR, logo_selector)
                    logo_url = logo_elem.get_attribute("src")
                    if logo_url:
                        logger.debug(f"Found logo URL: {logo_url}")
                        break
                except NoSuchElementException:
                    continue
        except Exception as e:
            logger.debug(f"Error extracting logo: {str(e)}")
        
        # Enhanced phone number extraction
        phone = ""
        try:
            # Check about page for contact info
            contact_section = self.driver.find_elements(By.CSS_SELECTOR, ".org-page-details-module__card-spacing")
            
            for section in contact_section:
                try:
                    dt_elements = section.find_elements(By.TAG_NAME, "dt")
                    for dt in dt_elements:
                        if "phone" in dt.text.lower():
                            dd = dt.find_element(By.XPATH, "following-sibling::dd")
                            phone = dd.text.strip()
                            logger.debug(f"Found phone: {phone}")
                            break
                except:
                    continue
            
            # If still no phone, try other selectors
            if not phone:
                phone = self.get_text_safely(".org-top-card__primary-content .org-contact-info__contact-type") or \
                        self.get_text_safely(".org-contact-info-card") or \
                        self.get_text_safely(".org-page-details-module__info-item--phone")
        except Exception as e:
            logger.debug(f"Error extracting phone number: {str(e)}")
                
        # Try to get headcount if available
        headcount_text = self.get_text_safely(".org-top-card-summary-info-list__info-item") or \
                         self.get_text_safely(".org-about-company-module__company-staff-count-range")
        headcount = None
        if headcount_text:
            match = re.search(r'(\d+,?\d*)', headcount_text)
            if match:
                try:
                    headcount = int(match.group(1).replace(',', ''))
                except:
                    pass
        
        # Navigate to About page
        about_url = f"{url}about/"
        self.driver.get(about_url)
        time.sleep(3)
        
        # Scroll to load content
        for _ in range(2):
            self.scroll_down()
        
        # About us text - try multiple selectors
        about_us = self.get_text_safely(".org-about-us-organization-description__text") or \
                   self.get_text_safely(".break-words.white-space-pre-wrap") or \
                   self.get_text_safely(".org-page-details-module__description-content")
        
        # Get all dt/dd pairs which contain company details
        raw_details = {}
        try:
            detail_sections = self.driver.find_elements(By.CSS_SELECTOR, ".org-page-details-module__card-spacing")
            for section in detail_sections:
                try:
                    dts = section.find_elements(By.TAG_NAME, "dt")
                    dds = section.find_elements(By.TAG_NAME, "dd")
                    
                    for i, dt in enumerate(dts):
                        if i < len(dds):
                            key = dt.text.strip()
                            value = dds[i].text.strip()
                            raw_details[key] = value
                            logger.debug(f"Found detail: {key}: {value}")
                except Exception as e:
                    logger.debug(f"Error getting details: {str(e)}")
        except Exception as e:
            logger.debug(f"Error finding detail sections: {str(e)}")
        
        # Initialize company data fields with empty values
        industry = ""
        headquarters = ""
        company_size = ""
        founded = ""
        specialties = ""
        company_type = ""
        
        # FIRST PASS: Process fields with clear labels based on LinkedIn's field names
        for key, value in raw_details.items():
            key_lower = key.lower()
            
            # Only assign values that aren't about "associated members"
            if self.has_associated_members(value):
                logger.debug(f"Skipping value with 'associated members': {key}: {value}")
                continue
                
            # Assign fields only if they match their expected content type
            if 'industry' in key_lower:
                industry = value
                logger.debug(f"Assigned industry: {value}")
            elif ('size' in key_lower or 'employees' in key_lower):
                if self.is_company_size(value):
                    company_size = value
                    logger.debug(f"Assigned company size: {value}")
            elif ('headquarters' in key_lower or 'location' in key_lower):
                if self.is_location(value):
                    headquarters = value
                    logger.debug(f"Assigned headquarters: {value}")
            elif 'founded' in key_lower or 'established' in key_lower:
                if self.is_year(value):
                    founded = value
                    logger.debug(f"Assigned founded year: {value}")
            elif 'specialties' in key_lower or 'expertise' in key_lower:
                if self.is_specialties(value):
                    specialties = value
                    logger.debug(f"Assigned specialties: {value}")
            elif 'type' in key_lower:
                company_type = value
                logger.debug(f"Assigned company type: {value}")
        
        # SECOND PASS: Process unlabeled or misplaced values by content analysis
        for key, value in raw_details.items():
            # Skip if value has "associated members" or is already assigned to a field
            if self.has_associated_members(value) or value in [industry, headquarters, company_size, founded, specialties]:
                continue
                
            # Check for years (exact 4-digit year format)
            if not founded and self.is_year(value):
                # Only years between 1900-2030 are valid founding years
                year_match = re.match(r'^(19[0-9]{2}|20[0-3][0-9])$', value.strip())
                if year_match:
                    founded = value
                    logger.debug(f"Found year value for founded: {value}")
            
            # Detect location formats (City, State/Province or City, Country)
            elif not headquarters and self.is_location(value):
                location_match = re.match(r'^[A-Za-z\s\-\.]+,\s*[A-Za-z\s\-\.]+$', value)
                if location_match:
                    headquarters = value
                    logger.debug(f"Found location value for headquarters: {value}")
            
            # Company size typically contains employee counts or ranges
            elif not company_size and self.is_company_size(value):
                company_size = value
                logger.debug(f"Found company size from content: {value}")
            
            # Specialties are typically comma-separated lists
            elif not specialties and ',' in value and value.count(',') >= 2:
                specialties = value
                logger.debug(f"Found specialties from comma-separated list: {value}")
        
        # THIRD PASS: Remove any "associated members" text that might have been assigned
        if headquarters and self.has_associated_members(headquarters):
            logger.debug(f"Clearing headquarters with 'associated members': {headquarters}")
            headquarters = ""
            
        if company_size and self.has_associated_members(company_size):
            logger.debug(f"Clearing company_size with 'associated members': {company_size}")
            company_size = ""
            
        if founded and self.has_associated_members(founded):
            logger.debug(f"Clearing founded with 'associated members': {founded}")
            founded = ""
            
        if specialties and self.has_associated_members(specialties):
            logger.debug(f"Clearing specialties with 'associated members': {specialties}")
            specialties = ""
        
        # FOURTH PASS: Check for data in wrong fields and fix ONLY if confident
        
        # If founded field contains a location but not a year, clear it
        if founded and not self.is_year(founded):
            logger.debug(f"Clearing non-year value from founded field: {founded}")
            founded = ""
        
        # If headquarters contains only a number (likely year), clear it
        if headquarters and re.match(r'^\d+$', headquarters.strip()):
            logger.debug(f"Clearing numeric-only value from headquarters: {headquarters}")
            headquarters = ""
        
        # If specialties is just a year, clear it
        if specialties and self.is_year(specialties) and len(specialties.strip()) <= 5:
            logger.debug(f"Clearing year value from specialties: {specialties}")
            specialties = ""
        
        # Get showcase pages and affiliated companies
        showcase_pages = []
        affiliated_companies = []
        
        try:
            # Look for "Related Companies" section
            related_section = self.get_text_safely(".org-related-companies-module")
            if related_section:
                # Try to find and click the "Show more" button if present
                try:
                    show_more = self.driver.find_element(By.CSS_SELECTOR, ".org-related-companies-module__show-more-btn")
                    show_more.click()
                    time.sleep(2)
                except:
                    pass
                    
                # Extract showcase pages
                try:
                    showcase_elements = self.driver.find_elements(By.CSS_SELECTOR, ".org-related-companies-module__showcase .org-company-card")
                    for element in showcase_elements:
                        try:
                            company_name = element.find_element(By.CSS_SELECTOR, ".org-company-card__title").text.strip()
                            company_url = element.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                            followers = element.find_element(By.CSS_SELECTOR, ".org-company-card__followers").text.strip()
                            showcase_pages.append({
                                "name": company_name,
                                "linkedin_url": company_url,
                                "followers": followers
                            })
                        except:
                            pass
                except:
                    pass
                    
                # Extract affiliated companies
                try:
                    affiliated_elements = self.driver.find_elements(By.CSS_SELECTOR, ".org-related-companies-module__affiliated .org-company-card")
                    for element in affiliated_elements:
                        try:
                            company_name = element.find_element(By.CSS_SELECTOR, ".org-company-card__title").text.strip()
                            company_url = element.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                            followers = element.find_element(By.CSS_SELECTOR, ".org-company-card__followers").text.strip()
                            affiliated_companies.append({
                                "name": company_name,
                                "linkedin_url": company_url,
                                "followers": followers
                            })
                        except:
                            pass
                except:
                    pass
        except Exception as e:
            logger.debug(f"Error extracting related companies: {str(e)}")
        
        # Get leadership profiles (up to 5)
        leadership = self.get_leadership_profiles(url, max_leaders=5)

        
        employees = self.get_regular_employees(url, max_employees=5)
        
        # Create structured company data object (matching the preferred format from IBM example)
        company_data = {
            "JobDetails": {
                "companyInfo": {
                    "portal": "LinkedIn",
                    "name": company_name,
                    "offices": [],
                    "industry": industry,
                    "description": {
                        "text": about_us,
                        "html": about_us,
                        "vision": ""
                    },
                    "url": url,
                    "website": website,
                    "phone": phone,
                    "logo": logo_url,
                    "rating": None,
                    "reviewsCount": None,
                    "openings": None,
                    "commitments": {
                        "_ids": [],
                        "names": specialties.split(", ") if specialties else []
                    },
                    "leadership": leadership,
                    "companyInsight": {
                        "financialInsight": {}
                    },
                    "companyType": company_type,
                    "showcasePages": showcase_pages,
                    "affiliatedCompanies": affiliated_companies,
                    "foundedYear": founded,
                    "companySize": company_size,
                    "headcount": headcount,
                    "isFeatured": False
                }
            },
            "CompanyData": {
                "rating": [],
                "reviews": []
            }
        }
        
        # Add headquarters to offices if available
        if headquarters:
            location_parts = headquarters.split(", ")
            company_data["JobDetails"]["companyInfo"]["offices"].append({
                "location": {
                    "area": "",
                    "city": location_parts[0] if len(location_parts) > 0 else "",
                    "state": location_parts[1] if len(location_parts) > 1 else "",
                    "country": location_parts[2] if len(location_parts) > 2 else 
                              (location_parts[1] if len(location_parts) > 1 else "")
                }
            })
        
        # Also include the flat structure for backward compatibility
        company_data["raw_data"] = {
            "name": company_name,
            "about_us": about_us,
            "website": website,
            "phone": phone,
            "headquarters": headquarters,
            "founded": founded,
            "industry": industry,
            "company_type": company_type,
            "company_size": company_size,
            "specialties": specialties,
            "showcase_pages": showcase_pages,
            "affiliated_companies": affiliated_companies,
            "employees": employees,
            "headcount": headcount,
            "linkedin_url": url
        }
        
        # Log success
        logger.info(f"Successfully scraped company data for: {company_name}")
        
        return company_data
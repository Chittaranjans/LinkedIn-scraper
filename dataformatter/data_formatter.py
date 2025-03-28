import re
import json
import os
import logging
from datetime import datetime

class LinkedInFormatter:
    def __init__(self):
        self.logger = logging.getLogger("linkedin_formatter")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.FileHandler("formatter.log")
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def clean_text(self, text):
        """Clean and format text by removing extra spaces and HTML tags"""
        if not text:
            return ""
            
        # Convert to string if not already
        text = str(text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Replace multiple spaces/newlines with single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def format_company_data(self, company):
        """Format company data to match the desired schema"""
        try:
            # Create the base structure following company.json format
            company_data = {
                "JobDetails": {
                    "companyInfo": {
                        "portal": "LinkedIn",
                        "name": self.clean_text(getattr(company, 'name', '')),
                        "offices": [],
                        "industry": self.clean_text(getattr(company, 'industry', '')),
                        "description": {
                            "text": self.clean_text(getattr(company, 'about_us', '')),
                            "html": self.clean_text(getattr(company, 'about_us', '')),
                            "vision": ""
                        },
                        "url": getattr(company, 'linkedin_url', ''),
                        "website": self.clean_text(getattr(company, 'website', '')),
                        "logo": "",
                        "rating": None,
                        "reviewsCount": None,
                        "openings": None,
                        "commitments": {
                            "_ids": [],
                            "names": []
                        },
                        "leadership": [],
                        "companyInsight": {
                            "financialInsight": {
                                "currentStage": "",
                                "keyInvestors": ""
                            },
                            "gallery": [],
                            "benefits": []
                        },
                        "isFeatured": False
                    }
                },
                "CompanyData": {
                    "rating": [],
                    "reviews": []
                }
            }
            
            # Add company specialties as commitments
            if hasattr(company, 'specialties') and company.specialties:
                specialties = [s.strip() for s in company.specialties.split(',') if s.strip()]
                company_data["JobDetails"]["companyInfo"]["commitments"]["names"] = specialties
            
            # Add headquarters location
            if hasattr(company, 'headquarters') and company.headquarters:
                location = company.headquarters.strip()
                location_parts = location.split(', ')
                
                office = {
                    "location": {
                        "area": "",
                        "city": location_parts[0] if len(location_parts) > 0 else "",
                        "state": location_parts[1] if len(location_parts) > 1 else "",
                        "country": location_parts[-1] if len(location_parts) > 0 else ""
                    }
                }
                company_data["JobDetails"]["companyInfo"]["offices"].append(office)
            
            # Add employees as leadership
            if hasattr(company, 'employees') and company.employees:
                for i, employee in enumerate(company.employees):
                    if i >= 5:  # Limit to 5 leaders
                        break
                        
                    if isinstance(employee, dict):
                        name = employee.get('name', '')
                        position = employee.get('designation', '')
                        url = employee.get('linkedin_url', '')
                    else:
                        name = getattr(employee, 'name', '')
                        position = getattr(employee, 'designation', '')
                        url = getattr(employee, 'linkedin_url', '')
                        
                    leadership_entry = {
                        "url": url,
                        "logo": "",
                        "name": self.clean_text(name),
                        "position": self.clean_text(position)
                    }
                    company_data["JobDetails"]["companyInfo"]["leadership"].append(leadership_entry)
            
            # Add company size if available
            if hasattr(company, 'company_size') and company.company_size:
                company_data["JobDetails"]["companyInfo"]["companySize"] = self.clean_text(company.company_size)
            
            # Add founded year if available
            if hasattr(company, 'founded') and company.founded:
                company_data["JobDetails"]["companyInfo"]["foundedYear"] = self.clean_text(company.founded)
            
            return company_data
            
        except Exception as e:
            self.logger.error(f"Error formatting company data: {str(e)}")
            # Return basic data structure with error
            return {
                "JobDetails": {
                    "companyInfo": {
                        "name": getattr(company, 'name', 'Unknown'),
                        "error": str(e),
                        "url": getattr(company, 'linkedin_url', '')
                    }
                }
            }
    
    def format_company_data_from_dict(self, company_data):
        """Format company data from custom scraper dictionary"""
        if "JobDetails" in company_data:
            # Already in the correct format
            return company_data
        
        # Create the base structure following your schema
        formatted_data = {
            "JobDetails": {
                "companyInfo": {
                    "portal": "LinkedIn",
                    "name": self.clean_text(company_data.get('name', '')),
                    "offices": [],
                    "industry": self.clean_text(company_data.get('industry', '')),
                    "description": {
                        "text": self.clean_text(company_data.get('about_us', '')),
                        "html": self.clean_text(company_data.get('about_us', '')),
                        "vision": ""
                    },
                    "url": company_data.get('linkedin_url', ''),
                    "website": self.clean_text(company_data.get('website', '')),
                    "phone": self.clean_text(company_data.get('phone', '')),
                    "logo": company_data.get('logo', ''),
                    "rating": None,
                    "reviewsCount": None,
                    "openings": None,
                    "commitments": {
                        "_ids": [],
                        "names": []
                    },
                    "leadership": company_data.get('employees', []),
                    "companyInsight": {
                        "financialInsight": {}
                    },
                    "showcasePages": company_data.get('showcase_pages', []),
                    "affiliatedCompanies": company_data.get('affiliated_companies', []),
                    "foundedYear": self.clean_text(company_data.get('founded', '')),
                    "companyType": self.clean_text(company_data.get('company_type', '')),
                    "companySize": self.clean_text(company_data.get('company_size', '')),
                    "headcount": company_data.get('headcount'),
                    "isFeatured": False
                }
            },
            "CompanyData": {
                "rating": [],
                "reviews": []
            }
        }
        
        # Add headquarters if available
        if company_data.get('headquarters'):
            location_parts = company_data['headquarters'].split(", ")
            formatted_data["JobDetails"]["companyInfo"]["offices"].append({
                "location": {
                    "area": "",
                    "city": location_parts[0] if len(location_parts) > 0 else "",
                    "state": location_parts[1] if len(location_parts) > 1 else "",
                    "country": location_parts[2] if len(location_parts) > 2 else 
                               (location_parts[1] if len(location_parts) > 1 else "")
                }
            })
        
        # Add specialties as commitments
        if company_data.get('specialties'):
            specialties = [s.strip() for s in company_data['specialties'].split(',') if s.strip()]
            formatted_data["JobDetails"]["companyInfo"]["commitments"]["names"] = specialties
        
        # Add leadership profiles
        if company_data.get('employees'):
            formatted_data["JobDetails"]["companyInfo"]["leadership"] = []
            for employee in company_data['employees']:
                if isinstance(employee, dict):
                    leadership_entry = {
                        "name": self.clean_text(employee.get('name', '')),
                        "position": self.clean_text(employee.get('designation', '')),
                        "url": employee.get('linkedin_url', ''),
                        "photo_url": employee.get('photo_url', '')
                    }
                    formatted_data["JobDetails"]["companyInfo"]["leadership"].append(leadership_entry)
        
        return formatted_data

    def format_profile_data(self, person):
        """Format profile data to match the desired schema"""
        try:
            # Basic profile information
            profile_data = {
                "name": self.clean_text(getattr(person, 'name', '')),
                "headline": self.clean_text(getattr(person, 'headline', '')),
                "location": self.clean_text(getattr(person, 'location', '')),
                "about": self.clean_text(getattr(person, 'about', '')),
                "experiences": [],
                "education": [],
                "skills": [],
                "linkedinUrl": getattr(person, 'linkedin_url', '')
            }
            
            # Add experiences
            if hasattr(person, 'experiences') and person.experiences:
                for exp in person.experiences:
                    experience = {
                        "title": self.clean_text(getattr(exp, 'position_title', '')),
                        "company": self.clean_text(getattr(exp, 'institution_name', '')),
                        "location": self.clean_text(getattr(exp, 'location', '')),
                        "fromDate": self.clean_text(getattr(exp, 'from_date', '')),
                        "toDate": self.clean_text(getattr(exp, 'to_date', '')),
                        "description": self.clean_text(getattr(exp, 'description', ''))
                    }
                    profile_data["experiences"].append(experience)
            
            # Add education
            if hasattr(person, 'educations') and person.educations:
                for edu in person.educations:
                    education = {
                        "school": self.clean_text(getattr(edu, 'institution_name', '')),
                        "degree": self.clean_text(getattr(edu, 'degree', '')),
                        "field": self.clean_text(getattr(edu, 'field_of_study', '')),
                        "fromDate": self.clean_text(getattr(edu, 'from_date', '')),
                        "toDate": self.clean_text(getattr(edu, 'to_date', ''))
                    }
                    profile_data["education"].append(education)
            
            # Add skills
            if hasattr(person, 'skills') and person.skills:
                profile_data["skills"] = [self.clean_text(skill) for skill in person.skills]
            
            return profile_data
            
        except Exception as e:
            self.logger.error(f"Error formatting profile data: {str(e)}")
            # Return basic data with error
            return {
                "name": getattr(person, 'name', 'Unknown'),
                "error": str(e),
                "linkedinUrl": getattr(person, 'linkedin_url', '')
            }
            
    def save_to_json(self, data, filename):
        """Save data to JSON file with timestamp"""
        try:
            # Create output directory if it doesn't exist
            output_dir = 'scraped_data'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Add timestamp to filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(output_dir, f"{filename}_{timestamp}.json")
            
            # Write data to file with pretty formatting
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Data saved to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving JSON data: {str(e)}")
            return None
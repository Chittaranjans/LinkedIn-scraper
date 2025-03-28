import os
import json
import logging
from datetime import datetime

class JobFormatter:
    def __init__(self, output_dir='scraped_data'):
        self.output_dir = output_dir
        self.logger = logging.getLogger("job_formatter")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def format_job_data(self, job):
        """Format job data from Job object or dictionary for output"""
        try:
            # Handle both Job objects and dictionaries
            if isinstance(job, dict):
                job_data = job
            else:
                job_data = {
                    "job_title": getattr(job, "job_title", ""),
                    "company": getattr(job, "company", ""),
                    "company_linkedin_url": getattr(job, "company_linkedin_url", ""),
                    "location": getattr(job, "location", ""),
                    "posted_date": getattr(job, "posted_date", ""),
                    "applicant_count": getattr(job, "applicant_count", ""),
                    "job_description": getattr(job, "job_description", ""),
                    "benefits": getattr(job, "benefits", ""),
                    "linkedin_url": getattr(job, "linkedin_url", ""),
                    "requirements": getattr(job, "requirements", []),
                    "technical_skills": getattr(job, "technical_skills", []),
                    "company_data": getattr(job, "company_data", {})
                }
            
            # Ensure all fields exist
            required_fields = [
                "job_title", "company", "company_linkedin_url", "location", 
                "posted_date", "applicant_count", "job_description", "benefits", 
                "linkedin_url", "requirements", "technical_skills", "company_data"
            ]
            
            for field in required_fields:
                if field not in job_data:
                    if field in ["requirements", "technical_skills"]:
                        job_data[field] = []
                    elif field == "company_data":
                        job_data[field] = {}
                    else:
                        job_data[field] = ""
            
            return job_data
            
        except Exception as e:
            self.logger.error(f"Error formatting job data: {str(e)}")
            # Return minimal job data
            return {
                "error": str(e),
                "job_title": getattr(job, "job_title", "") if not isinstance(job, dict) else job.get("job_title", "Unknown"),
                "linkedin_url": getattr(job, "linkedin_url", "") if not isinstance(job, dict) else job.get("linkedin_url", "")
            }
    
    def save_to_json(self, data, filename):
        """Save data to JSON file with timestamp"""
        try:
            # Add timestamp to filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.output_dir, f"{filename}_{timestamp}.json")
            
            # Save the data
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Job data saved to {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Error saving job data to JSON: {str(e)}")
            return None
# LinkedIn Data Acquisition System
1. Overview
``` bash 
A comprehensive solution for extracting structured professional data from LinkedIn at scale. This system enables automated collection of job listings, company profiles, and professional data while implementing robust anti-detection measures and session management.
# CHECK SAMAPLE DATASCRAPES IN /scraped_data . 
```
2. Features
- 🔍 Multi-Entity Scraping: Jobs, companies, and professional profiles
- 🔐 Advanced Authentication: Cookie-based with credential fallback
- 🔄 Proxy Rotation: Intelligent proxy management with failure detection
- 🛡️ Anti-Detection Measures: Avoid being blocked by LinkedIn
- 🧩 Structured Data Output: Clean, consistent JSON formatting
- 🚀 API-First Design: RESTful endpoints for programmatic access
- 🏢 Production-Ready: Error handling and robust recovery mechanisms

```bash
linkedin_scraper/
├── app/                      # Main application framework
│   ├── api/                  # REST API endpoints
│   ├── core/                 # Configuration and middleware
│   ├── db/                   # Database connections
│   └── scrapers/             # High-level scraper implementations
├── utils/                    # Utility functions and helpers
│   ├── cookie_auth.py        # Authentication management
│   ├── proxy_handler.py      # Proxy rotation system
│   └── browser_setup.py      # Browser configuration helpers
├── linkedin_scraper/         # Core scraping logic
├── dataformatter/            # Data processing and formatting
├── create_cookies.py         # Authentication cookie generator
├── main.py                   # Basic scraper implementation (Direct Run)
├── scrape_jobs.py            # Only Jobs scraper implementation (Direct Run)
├── demo.py                   # Advanced scraper with proxy support (Direct Run)
└── README.md                 # This documentation file
```
### Installation
```bash
git clone https://github.com/yourusername/linkedin_scraper.git
cd linkedin_scraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

#Cookies Crate
python create_cookies.py 

# Server Start 
uvicron app.main:app --reload

# Set up environment variables
cp .env.example .env

```
## Quick Start
1. Generate Authentication Cookies
- Before running any scraping tasks, generate authentication cookies:
```bash
python create_cookies.py
```
* This script will:

- Launch a Chrome browser
- Log in to LinkedIn with your credentials
- Save authentication cookies for future use
- Take a screenshot of successful login
```bash
python main.py
```
* The main.py script provides a simple interface for scraping LinkedIn entities:

- Authenticates using saved cookies
- Extracts data from companies and profiles
- Saves structured data to JSON files

1. Advanced Usage with demo.py
```bash
python demo.py
```
* The demo.py script offers enhanced functionality:

- Proxy rotation with automatic failover
- Robust retry logic for failed requests
- Advanced error handling and logging
- Example usage of the scraping API

### REST API Endpoints
1. The system exposes RESTful API endpoints:
```bash
Jobs API

POST /api/jobs/search - Search for jobs with filters
POST /api/jobs/scrape - Scrape a specific job by URL
GET /api/jobs/{job_id} - Retrieve job by ID
GET /api/jobs/ - List all jobs with pagination

Companies API

POST /api/companies/scrape - Scrape a company profile
GET /api/companies/{company_id} - Retrieve company by ID
GET /api/companies/search - Search companies with filters

Profiles API

POST /api/profiles/scrape - Scrape a personal profile
GET /api/profiles/{profile_id} - Retrieve profile by ID
GET /api/profiles/search - Search profiles with filters

```

### Configuration

1. Key environment variables:
```bash 
LINKEDIN_USER=your_email@example.com
LINKEDIN_PASSWORD=your_secure_password
USE_PROXIES=true
PROXY_LIST_PATH=proxies.txt
COOKIE_PATH=cookies/linkedin_cookies.pkl
LOG_LEVEL=INFO
DB_URL = ****
```
### Contribution
``` bash
Contributions are welcome! Please feel free to submit a Pull Request.
```


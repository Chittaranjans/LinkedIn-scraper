VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
UVICORN = $(VENV)/bin/uvicorn
API_PORT = 8000
API_HOST = 0.0.0.0


DIRS = cookies logs scraped_data cookie_backups

.PHONY: all
all: setup cookies run-server


.PHONY: setup
setup: $(VENV) directories

$(VENV):
    python -m venv $(VENV)
    $(PIP) install -r requirements.txt

.PHONY: directories
directories:
    @echo "Creating necessary directories..."
    @mkdir -p $(DIRS)

# Cookie management
.PHONY: cookies
cookies:
    @echo "Generating LinkedIn cookies..."
    $(PYTHON) create_cookies.py

# .PHONY: check-cookies
# check-cookies:
#     @echo "Checking cookie health..."
#     $(PYTHON) scripts/check_cookie_health.py

.PHONY: run-server
run-server:
    @echo "Starting LinkedIn Scraper API server on $(API_HOST):$(API_PORT)..."
    $(UVICORN) app.main:app --host $(API_HOST) --port $(API_PORT)


# Direct script execution
.PHONY: run-main
run-main:
    @echo "Running basic scraper (main.py)..."
    $(PYTHON) main.py

.PHONY: run-demo
run-demo:
    @echo "Running advanced scraper with proxy support (demo.py)..."
    $(PYTHON) demo.py

.PHONY: scrape-jobs
scrape-jobs:
    @echo "Running job scraper (scrape_jobs.py)..."
    $(PYTHON) scrape_jobs.py

# Database setup
.PHONY: setup-db
setup-db:
    @echo "Setting up MongoDB indexes..."
    $(PYTHON) app/db/setup_indexes.py

# Clean up
.PHONY: clean-logs
clean-logs:
    @echo "Cleaning logs older than 7 days..."
    find logs -type f -name "*.log" -mtime +7 -delete

.PHONY: clean-all
clean-all:
    @echo "Removing virtual environment and generated files..."
    rm -rf $(VENV) logs/*.log *.png

.PHONY: help
help:
    @echo "LinkedIn Scraper Make Commands:"
    @echo "  make setup          - Create virtual environment and install dependencies"
    @echo "  make cookies        - Generate LinkedIn authentication cookies"
    @echo "  make check-cookies  - Check if cookies are still valid"
    @echo "  make run-server     - Start the API server"
    @echo "  make dev-server     - Start the API server in development mode with auto-reload"
    @echo "  make run-main       - Run the basic scraper (main.py)"
    @echo "  make run-demo       - Run the advanced scraper with proxies (demo.py)"
    @echo "  make scrape-jobs    - Run the job scraper (scrape_jobs.py)"
    @echo "  make setup-db       - Set up MongoDB indexes"
    @echo "  make clean-logs     - Remove log files older than 7 days"
    @echo "  make clean-all      - Remove virtual environment and all generated files"
    @echo "  make help           - Display this help message"
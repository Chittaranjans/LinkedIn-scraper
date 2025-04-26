import asyncio
import logging
import time
import json
import os
import sys
from datetime import datetime

from orchestrator import LinkedInScraperOrchestrator
from utils.logging_config import LoggingConfig
from dotenv import load_dotenv

# Configure logging
logger = LoggingConfig.setup_logging("small_scale_test")
load_dotenv()

def json_serializable(obj):
    """Handle datetime serialization for JSON"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not JSON serializable")

async def run_small_scale_test(concurrency=2, max_urls=10, use_proxies=False):
    """Run only a small-scale test with limited URLs"""
    logger.info("=== RUNNING SMALL SCALE TEST ===")
    
    # First verify cookies work
    from test_cookies import test_cookies
    
    if not test_cookies():
        logger.warning("Cookie test failed! You may need to regenerate cookies.")
        if "--force" not in sys.argv:
            return None
        logger.warning("Proceeding anyway due to --force flag")
    
    # Load test URLs
    try:
        with open('test_company_urls.json', 'r') as f:
            urls = json.load(f)
            if isinstance(urls, list) and len(urls) > 0:
                logger.info(f"Loaded {len(urls)} URLs from file")
    except:
        urls = [
            "https://www.linkedin.com/company/microsoft/",
            "https://www.linkedin.com/company/google/",
            "https://www.linkedin.com/company/apple/",
            "https://www.linkedin.com/company/amazon/",
            "https://www.linkedin.com/company/meta/"
        ]
        logger.info(f"Using {len(urls)} default test URLs")
    
    # Take just the first few URLs for the small test
    test_urls = urls[:min(max_urls, len(urls))]
    logger.info(f"Testing with {len(test_urls)} URLs")
    
    # Initialize the orchestrator with direct authentication option
    orchestrator = LinkedInScraperOrchestrator(max_browsers=concurrency, use_proxies=use_proxies)
    
    try:
        # Set up the orchestrator
        logger.info("Setting up orchestrator...")
        await orchestrator.setup()
        
        # Reset scheduler to ensure clean state
        orchestrator.scheduler.clear_stale_tasks()
        
        # Run the bulk scrape
        logger.info(f"Starting bulk scrape with concurrency={concurrency}...")
        start_time = time.time()
        
        result = await orchestrator.bulk_scrape_companies(test_urls, concurrency=concurrency)
        
        # Calculate results
        duration = time.time() - start_time
        
        # Report results
        logger.info("=== TEST RESULTS ===")
        logger.info(f"Total URLs: {result['total']}")
        logger.info(f"Completed: {result['completed']}")
        logger.info(f"Failed: {result['failed']}")
        logger.info(f"Success Rate: {(result['completed']/result['total'])*100:.1f}%")
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"Processing Rate: {result['urls_per_minute']:.1f} URLs/minute")
        
        # Write detailed results to file
        detailed_results = {
            "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": result,
            "completed_tasks": {k: v for k, v in orchestrator.completed_tasks.items()},
            "failed_tasks": {k: v for k, v in orchestrator.failed_tasks.items()}
        }
        
        with open("small_scale_results.json", "w") as f:
            json.dump(detailed_results, f, indent=2, default=json_serializable)
        
        logger.info("Detailed results saved to small_scale_results.json")
        
        return result
        
    except Exception as e:
        logger.error(f"Test encountered an error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    
    finally:
        # Always clean up resources
        logger.info("Cleaning up resources...")
        await orchestrator.cleanup()

if __name__ == "__main__":
    # Parse command line args
    concurrency = 2
    use_proxies = True
    max_urls = 10
    
    # Process command line args
    for arg in sys.argv[1:]:
        if arg == "--no-proxy":
            use_proxies = False
        elif arg.startswith("--concurrency="):
            try:
                concurrency = int(arg.split("=")[1])
            except:
                pass
        elif arg.startswith("--max-urls="):
            try:
                max_urls = int(arg.split("=")[1])
            except:
                pass
    
    # Run the test
    asyncio.run(run_small_scale_test(
        concurrency=concurrency, 
        max_urls=max_urls,
        use_proxies=use_proxies
    ))
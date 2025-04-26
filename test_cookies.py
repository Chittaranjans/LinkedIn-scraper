import os
import time
import pickle
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("cookie_tester")

def test_cookies():
    logger.info("Testing LinkedIn cookies...")
    
    # Check if cookie file exists
    cookie_file = os.path.join('cookies', 'linkedin_cookies.pkl')
    if not os.path.exists(cookie_file):
        logger.error(f"Cookie file not found: {cookie_file}")
        return False
    
    # Create a browser without proxy to test cookies
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    try:
        # First load LinkedIn domain
        logger.info("Loading LinkedIn home page...")
        driver.get("https://www.linkedin.com")
        time.sleep(3)
        
        # Load cookies
        logger.info("Loading cookies...")
        with open(cookie_file, 'rb') as f:
            cookies = pickle.load(f)
        
        logger.info(f"Found {len(cookies)} cookies")
        
        # Add cookies
        for cookie in cookies:
            try:
                # Fix expiry if needed
                if 'expiry' in cookie and isinstance(cookie['expiry'], float):
                    cookie['expiry'] = int(cookie['expiry'])
                
                # Skip problematic cookies
                if 'domain' not in cookie:
                    continue
                    
                driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(f"Could not add cookie: {e}")
        
        # Refresh and navigate to feed
        driver.refresh()
        time.sleep(2)
        
        logger.info("Navigating to feed...")
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(5)
        
        # Take a screenshot
        os.makedirs("screenshots", exist_ok=True)
        screenshot_path = os.path.join("screenshots", "cookie_test.png")
        driver.save_screenshot(screenshot_path)
        logger.info(f"Screenshot saved to {screenshot_path}")
        
        # Check URL
        if "feed" in driver.current_url:
            logger.info("COOKIES WORKING CORRECTLY")
            return True
        else:
            logger.error(f"COOKIES FAILED - Current URL: {driver.current_url}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing cookies: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        driver.quit()

if __name__ == "__main__":
    result = test_cookies()
    print(f"Cookie Test Result: {'SUCCESS' if result else 'FAILED'}")
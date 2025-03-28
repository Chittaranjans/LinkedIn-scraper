import os
import time
import logging
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.cookie_auth import LinkedInCookieAuth
from utils.browser_setup import BrowserSetup
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_USER = os.getenv('LINKEDIN_USER')
LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('cookie_creator')

def main():
    # Create required directories first
    try:
        os.makedirs('cookies', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        logger.info("Created necessary directories")
    except Exception as e:
        logger.warning(f"Could not create directories: {str(e)}")
    
    # Create browser with anti-detection features
    browser_setup = BrowserSetup()
    chrome_options = Options()
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--no-sandbox')
    
    logger.info("Creating browser...")
    driver = browser_setup.create_driver(chrome_options, headless=False)
    
    if not driver:
        logger.error("Failed to create browser")
        return False
    
    # Initialize auth helper
    auth_helper = LinkedInCookieAuth(driver)
    
    # Modify user agent for less detection
    try:
        # Modern approach using Chrome DevTools Protocol
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        logger.info("Applied CDP script to hide webdriver flag")
    except Exception as e:
        logger.warning(f"Could not apply stealth script: {str(e)}")
        # Continue anyway - this is not critical
    
    # Try to authenticate
    logger.info("Attempting login...")
    
    # Go directly to login page
    driver.get('https://www.linkedin.com/login')
    time.sleep(3)
    
    # Check if we need to handle a different page variant
    page_source = driver.page_source.lower()
    if "sign in" in page_source:
        logger.info("Standard login page detected")
        
        # Find username field using multiple methods
        try:
            # Try different selectors with explicit wait
            username_field = None
            for selector in ["#username", "input[name='session_key']", "#email-or-phone", "input[type='text']"]:
                try:
                    username_field = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if username_field:
                        logger.info(f"Found username field with selector: {selector}")
                        break
                except:
                    continue
            
            if not username_field:
                raise Exception("Username field not found")
                
            # Find password field
            password_field = None
            for selector in ["#password", "input[name='session_password']", "input[type='password']"]:
                try:
                    password_field = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if password_field:
                        logger.info(f"Found password field with selector: {selector}")
                        break
                except:
                    continue
                    
            if not password_field:
                raise Exception("Password field not found")
            
            # Enter credentials with human-like delays
            username_field.clear()
            for char in LINKEDIN_USER:
                username_field.send_keys(char)
                time.sleep(0.1)
                
            time.sleep(1)
            
            password_field.clear()
            for char in LINKEDIN_PASSWORD:
                password_field.send_keys(char)
                time.sleep(0.1)
                
            time.sleep(1)
            
            # Find sign in button
            signin_button = None
            for selector in ["button[type='submit']", "button.btn__primary--large", 
                           "button[aria-label='Sign in']", "button:contains('Sign in')"]:
                try:
                    signin_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if signin_button:
                        logger.info(f"Found signin button with selector: {selector}")
                        break
                except:
                    continue
                    
            if not signin_button:
                signin_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in')]")
            
            if not signin_button:
                raise Exception("Sign in button not found")
                
            # Click sign in
            signin_button.click()
            logger.info("Clicked sign in button")
            time.sleep(5)
            
            # Wait for successful login
            max_wait = 30
            start_time = time.time()
            while time.time() - start_time < max_wait:
                if "feed" in driver.current_url:
                    logger.info("Successfully logged in!")
                    break
                time.sleep(1)
            
            # Check if login was successful
            if "feed" in driver.current_url:
                # Create cookies directory
                os.makedirs('cookies', exist_ok=True)
                
                # Save cookies
                auth_helper.cookie_file = 'cookies/linkedin_cookies.pkl'
                auth_helper.save_cookies(driver)
                logger.info("Cookies saved successfully")
                
                # Copy cookies to standard location for API compatibility
                standard_path = 'cookies/linkedin_cookies.pkl'
                if auth_helper.cookie_file != standard_path:
                    shutil.copy(auth_helper.cookie_file, standard_path)
                    logger.info(f"Copied cookies to {standard_path}")
                
                # Take screenshot of successful login
                driver.save_screenshot("login_success.png")
                logger.info("Login successful! Cookies saved.")
                
                return True
            else:
                logger.error(f"Failed to login. Current URL: {driver.current_url}")
                driver.save_screenshot("login_failure.png")
                return False
                
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            driver.save_screenshot("login_error.png")
            return False
    else:
        logger.error("Unexpected page encountered")
        driver.save_screenshot("unexpected_page.png")
        return False

if __name__ == "__main__":
    main()
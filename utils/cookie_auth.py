import os
import json
import time
import pickle
import logging
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from utils.logging_config import LoggingConfig

class LinkedInCookieAuth:
    def __init__(self, driver, cookie_file=None):
        self.driver = driver
        
        # Set default cookie path that works in all environments
        if cookie_file is None:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            self.cookie_file = os.path.join(project_root, 'cookies', 'linkedin_cookies.pkl')
            
            # Create cookies directory if needed
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
        else:
            self.cookie_file = cookie_file
            
        self.logger = LoggingConfig.setup_logging("linkedin_auth")
        
        # Debug information
        self.logger.info(f"Using cookie file: {self.cookie_file}")
        self.logger.info(f"Cookie file exists: {os.path.exists(self.cookie_file)}")
    
    def get_manual_login(self, driver, linkedin_user, linkedin_pass):
        """Guides user through manual login if needed"""
        try:
            driver.get('https://www.linkedin.com/login')
            time.sleep(3)
            
            # Try automated login first
            try:
                email_field = driver.find_element(By.ID, "username")
                password_field = driver.find_element(By.ID, "password")
                
                email_field.clear()
                email_field.send_keys(linkedin_user)
                time.sleep(1)
                password_field.clear()
                password_field.send_keys(linkedin_pass)
                time.sleep(1)
                
                submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                submit_button.click()
                time.sleep(5)
            except Exception as e:
                self.logger.error(f"Automated login failed: {str(e)}")
            
            # Check if we're on the feed page
            if "feed" in driver.current_url:
                self.logger.info("Automated login successful")
            else:
                # If not successful, guide the user to login manually
                print("\n" + "="*50)
                print("MANUAL LOGIN REQUIRED")
                print("="*50)
                print("1. Please login to LinkedIn in the browser window")
                print("2. Once logged in, return to this terminal")
                print("3. Press Enter when successfully logged in")
                print("="*50)
                
                input("Press Enter after successful login...")
            
            # Verify we're logged in
            if "feed" in driver.current_url or "mynetwork" in driver.current_url:
                print("Login successful! Saving session for future use.")
                self.save_cookies(driver)
                return True
            else:
                self.logger.warning(f"Login process may have failed. Current URL: {driver.current_url}")
                return False
        except Exception as e:
            self.logger.error(f"Manual login process error: {str(e)}")
            return False
    
    def save_cookies(self, driver):
        """Save cookies to file for later reuse"""
        try:
            cookies = driver.get_cookies()
            os.makedirs(os.path.dirname(os.path.abspath(self.cookie_file)), exist_ok=True)
            with open(self.cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            self.logger.info(f"Saved {len(cookies)} cookies to {self.cookie_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving cookies: {str(e)}")
            return False
    
    def load_cookies(self, driver):
        """Load cookies from file and add them to driver"""
        if not os.path.exists(self.cookie_file):
            self.logger.info("No cookie file found")
            return False
        
        try:
            with open(self.cookie_file, 'rb') as f:
                cookies = pickle.load(f)
            
            # Navigate to LinkedIn domain first
            driver.get('https://www.linkedin.com')
            time.sleep(2)
            
            for cookie in cookies:
                try:
                    # Some cookies can't be added directly
                    if 'expiry' in cookie:
                        # Selenium expects expiry as an int, not float
                        cookie['expiry'] = int(cookie['expiry'])
                    driver.add_cookie(cookie)
                except Exception as e:
                    pass
            
            self.logger.info(f"Successfully loaded {len(cookies)} cookies")
            return True
        except Exception as e:
            self.logger.error(f"Error loading cookies: {str(e)}")
            return False
    
    def verify_login(self, driver):
        """Verify if login using cookies was successful"""
        try:
            # Refresh or navigate to feed page
            driver.get('https://www.linkedin.com/feed/')
            time.sleep(3)
            
            # Check if we're logged in by looking for feed elements
            if "feed" in driver.current_url:
                # Try to find an element that only exists when logged in
                try:
                    driver.find_element(By.ID, "global-nav")
                    self.logger.info("Cookie login verified - user is logged in")
                    return True
                except:
                    self.logger.warning("Cookie login failed - user is not logged in")
                    return False
            else:
                self.logger.warning("Cookie login failed - redirected to login page")
                return False
        except Exception as e:
            self.logger.error(f"Error verifying login: {str(e)}")
            return False

    def authenticate_with_cookies(self):
        """Authenticate using saved cookies with improved error handling"""
        try:
            # Load cookies
            if not os.path.exists(self.cookie_file):
                self.logger.info("No cookie file found")
                return False
                
            # Try to handle SSL errors
            self.handle_ssl_errors()
            
            # Navigate first to home page with retry logic
            for attempt in range(3):
                try:
                    self.driver.get('https://www.linkedin.com')
                    break
                except Exception as e:
                    self.logger.warning(f"Error loading LinkedIn home: {str(e)}. Retrying ({attempt+1}/3)")
                    time.sleep(2 * (attempt + 1))
            
            # Load and apply cookies
            self.load_cookies(self.driver)
            
            # Add random delay to simulate human behavior
            time.sleep(random.uniform(2, 4))
            
            # Verify login with better error handling
            return self.verify_login(self.driver)
        except Exception as e:
            self.logger.error(f"Cookie authentication error: {str(e)}")
            return False
            
    def authenticate_with_credentials(self, username, password):
        """Authenticate using username and password with extra reliability for servers"""
        try:
            self.driver.get('https://www.linkedin.com/login')
            time.sleep(3)
            
            # Multiple selectors to try
            username_selectors = [
                (By.ID, "username"),
                (By.NAME, "session_key"),
                (By.CSS_SELECTOR, "input[name='session_key']"),
                (By.XPATH, "//input[@autocomplete='username']")
            ]
            
            # Try each selector
            email_field = None
            for selector_type, selector in username_selectors:
                try:
                    email_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    if email_field:
                        break
                except:
                    continue
                    
            if not email_field:
                self.logger.error("Could not find username field")
                return False
                
            # Try finding password field
            password_selectors = [
                (By.ID, "password"), 
                (By.NAME, "session_password"),
                (By.CSS_SELECTOR, "input[name='session_password']"),
                (By.XPATH, "//input[@autocomplete='current-password']")
            ]
            
            password_field = None
            for selector_type, selector in password_selectors:
                try:
                    password_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    if password_field:
                        break
                except:
                    continue
                    
            if not password_field:
                self.logger.error("Could not find password field")
                return False
                
            # Enter credentials with human-like delays
            email_field.clear()
            for char in username:
                email_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
                
            time.sleep(random.uniform(0.5, 1))
            
            password_field.clear()
            for char in password:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
                
            time.sleep(random.uniform(0.5, 1))
            
            # Find and click the login button
            submit_selectors = [
                (By.XPATH, "//button[@type='submit']"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(@class,'btn__primary')]"),
                (By.XPATH, "//button[contains(text(),'Sign in')]")
            ]
            
            submit_button = None
            for selector_type, selector in submit_selectors:
                try:
                    submit_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector))
                    )
                    if submit_button:
                        break
                except:
                    continue
                    
            if not submit_button:
                self.logger.error("Could not find submit button")
                return False
                
            # Click and wait
            submit_button.click()
            time.sleep(5)
            
            # Check if login successful
            return self.verify_login(self.driver)
        except Exception as e:
            self.logger.error(f"Login error: {str(e)}")
            return False

    def handle_ssl_errors(self):
        """Set browser options to handle SSL errors with proxies"""
        try:
            # Navigate to chrome://flags
            self.driver.get('chrome://flags/')
            time.sleep(1)
            
            # Execute JavaScript to change SSL error override setting
            self.driver.execute_script("""
            var input = document.querySelector('#search-input');
            if (input) {
                input.value = 'ssl';
                input.dispatchEvent(new Event('input'));
            }
            """)
            time.sleep(1)
            
            # Look for the SSL error handling option and enable it
            self.driver.execute_script("""
            var elements = document.querySelectorAll('.experiment-enabled-select');
            for (var i = 0; i < elements.length; i++) {
                if (elements[i].parentElement.textContent.includes('SSL certificate errors')) {
                    elements[i].value = '1';  // Set to Enabled
                    elements[i].dispatchEvent(new Event('change'));
                }
            }
            """)
            time.sleep(1)
            
            # Restart browser to apply changes
            self.driver.get('chrome://restart')
            time.sleep(5)
            
            return True
        except Exception as e:
            self.logger.error(f"Error handling SSL settings: {str(e)}")
            return False
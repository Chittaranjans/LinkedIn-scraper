import random
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class BrowserSetup:
    def __init__(self):
        self.logger = logging.getLogger("browser_setup")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.FileHandler("browser_setup.log")
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def create_driver(self, use_proxy=False, proxy=None, headless=False):
        """Create a Chrome driver with various options"""
        options = Options()
        
        # Handle SSL errors that are occurring
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--allow-insecure-localhost')
        
        # Basic performance options
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-notifications')
        
        # Add proxy if requested and specified
        if use_proxy and proxy:
            options.add_argument(f'--proxy-server={proxy}')
            self.logger.info(f"Using proxy: {proxy}")
        
        # Anti-detection options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Fix WebGL errors
        options.add_argument('--enable-unsafe-swiftshader')
        
        # Random window size
        width = random.randint(1200, 1600)
        height = random.randint(800, 1000)
        options.add_argument(f'--window-size={width},{height}')
        
        # Set headless mode if requested
        if headless:
            options.add_argument('--headless=new')
        
        # Random user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        user_agent = random.choice(user_agents)
        options.add_argument(f'user-agent={user_agent}')
        
        # Create the driver
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            
            # Set shorter timeouts to avoid long hangs
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            
            # Apply some JavaScript to avoid detection
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        except Exception as e:
            self.logger.error(f"Error creating Chrome driver: {str(e)}")
            return None
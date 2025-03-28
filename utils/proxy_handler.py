import random
import logging
import requests
import time
import urllib3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ProxyHandler:
    def __init__(self, proxy_file='proxies.txt', test_url='https://www.google.com'):
        self.proxy_file = proxy_file
        self.proxies = self.load_proxies()
        self.working_proxies = []
        self.failed_proxies = set()
        self.current_index = 0
        self.test_url = test_url
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        logger = logging.getLogger("proxy_handler")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.FileHandler("logs/proxy_handler.log")
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            logger.addHandler(console)
        return logger
    
    def load_proxies(self):
        """Load proxies from file and filter out empty lines and comments"""
        proxies = []
        try:
            with open(self.proxy_file, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('//'):
                        proxies.append(line)
            print(f"Loaded {len(proxies)} proxies from file")
        except FileNotFoundError:
            print(f"Proxy file {self.proxy_file} not found. Creating empty file.")
            with open(self.proxy_file, 'w') as file:
                pass
        return proxies
    
    def test_proxy(self, proxy):
        """Test if a proxy works with a basic connection test"""
        if not proxy or proxy in self.failed_proxies:
            return False
            
        try:
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml'
            }

            # Use a short timeout for testing
            response = requests.get(
                self.test_url,
                proxies=proxies,
                headers=headers,
                timeout=5,
                verify=False
            )
            
            # Check if proxy returns a successful response
            if response.status_code == 200:
                self.logger.info(f"Proxy {proxy} is working")
                return True
            else:
                self.failed_proxies.add(proxy)
                self.logger.info(f"Proxy {proxy} returned status code {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.failed_proxies.add(proxy)
            self.logger.debug(f"Proxy {proxy} failed: {str(e)}")
            return False
    
    def find_working_proxies(self, count=5, max_to_test=20):
        """Find working proxies by testing a random selection"""
        self.working_proxies = []
        
        # First try proxies we haven't marked as failed
        available_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        
        # If we're running low on options, reset and try all proxies again
        if len(available_proxies) < count:
            self.logger.info("Running out of untested proxies, resetting failed list")
            self.failed_proxies = set()
            available_proxies = self.proxies
        
        # Select random proxies to test
        test_proxies = random.sample(available_proxies, min(max_to_test, len(available_proxies)))
        
        self.logger.info(f"Testing {len(test_proxies)} proxies")
        for proxy in test_proxies:
            print(f"Testing proxy: {proxy}")
            if self.test_proxy(proxy):
                self.working_proxies.append(proxy)
                if len(self.working_proxies) >= count:
                    break
        
        self.logger.info(f"Found {len(self.working_proxies)} working proxies")
        return len(self.working_proxies) > 0
    
    def get_random_proxy(self):
        """Get a random working proxy"""
        if not self.working_proxies and not self.find_working_proxies():
            return None
        
        if not self.working_proxies:
            return None
            
        return random.choice(self.working_proxies)
    
    def mark_proxy_as_failed(self, proxy):
        """Mark a proxy as failed"""
        if proxy in self.working_proxies:
            self.working_proxies.remove(proxy)
        self.failed_proxies.add(proxy)
        
    def create_driver(self, use_proxy=True, headless=False):
        """Create a WebDriver with improved SSL handling for proxies"""
        options = Options()
        
        # Anti-detection options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # SSL error handling - CRITICAL for proxy usage
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--allow-insecure-localhost")
        options.add_argument("--ignore-ssl-errors=yes")
        
        # Performance options
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        
        # Add headless mode if requested
        if headless:
            options.add_argument("--headless=new")
        
        # Set window size
        options.add_argument("--window-size=1920,1080")
        
        # Add proxy if requested and available
        proxy = None
        if use_proxy:
            proxy = self.get_random_proxy()
            if proxy:
                options.add_argument(f'--proxy-server=http://{proxy}')
                self.logger.info(f"Using proxy: {proxy}")
        
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            
            # Anti-detection script
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver, proxy
            
        except Exception as e:
            self.logger.error(f"Error creating WebDriver: {str(e)}")
            return None, None
import random
import logging
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class ProxyRotator:
    def __init__(self, proxy_file='proxies.txt'):
        self.proxy_file = proxy_file
        self.proxies = self.load_proxies(proxy_file)
        self.current_index = 0
        self.working_proxies = []

    def load_proxies(self, file_path):
        proxies = []
        try:
            with open(file_path, 'r') as file:
                proxies = [line.strip() for line in file.readlines() if line.strip()]
            print(f"Loaded {len(proxies)} proxies from file")
        except FileNotFoundError:
            logging.error(f"Proxy file {file_path} not found.")
            print(f"Proxy file {file_path} not found. Creating empty file.")
            with open(file_path, 'w') as file:
                pass
        return proxies

    def get_next_proxy(self):
        # Try to get working proxies if none available
        if not self.working_proxies:
            self.refresh_working_proxies()

        if not self.working_proxies:
            logging.error("No working proxies available")
            print("No working proxies available. Running without proxy.")
            return None

        # Rotate through working proxies
        proxy = self.working_proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.working_proxies)
        return proxy

    def refresh_working_proxies(self):
        self.working_proxies = []
        print("Testing proxies for availability...")
        for proxy in self.proxies:
            print(f"Testing proxy: {proxy}")
            if self.test_proxy(proxy):
                self.working_proxies.append(proxy)
                print(f"Proxy {proxy} is working")
                if len(self.working_proxies) >= 5:  # Keep at least 5 working proxies
                    break
        print(f"Found {len(self.working_proxies)} working proxies")

    def test_proxy(self, proxy):
        try:
            test_url = 'https://www.linkedin.com'
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }

            response = requests.get(
                test_url,
                proxies=proxies,
                headers=headers,
                timeout=10,
                verify=False
            )

            return response.status_code == 200

        except Exception as e:
            logging.debug(f"Proxy {proxy} failed: {str(e)}")
            return False

    def filter_working_proxies(self):
        self.proxies = [proxy for proxy in self.proxies if self.test_proxy(proxy)]
        with open(self.proxy_file, 'w') as file:
            for proxy in self.proxies:
                file.write(f"{proxy}\n")
    
    def create_driver(self, headless=False):
        """Create a Selenium WebDriver with the next working proxy"""
        chrome_options = Options()
        
        # Add proxy if available
        proxy = self.get_next_proxy()
        if proxy:
            chrome_options.add_argument(f'--proxy-server=http://{proxy}')
            print(f"Using proxy: {proxy}")
        else:
            print("No proxy available, using direct connection")
        
        # Set headless mode if requested
        if headless:
            chrome_options.add_argument("--headless")
        
        # Anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-extensions")
        
        # User agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Create and return driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
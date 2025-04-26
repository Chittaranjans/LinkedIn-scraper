import os
import time
import logging
import pickle
import random
from datetime import datetime, timedelta

from utils.logging_config import LoggingConfig

logger = LoggingConfig.setup_logging("session_manager")

class LinkedInSessionManager:
    """Manages LinkedIn sessions for large-scale operations"""
    
    def __init__(self, cookie_dir="cookies"):
        self.cookie_dir = cookie_dir
        self.sessions = {}  # Cache of active sessions
        self.session_health = {}  # Track session health/success rate
        self.last_rotation = time.time()
        self.rotation_interval = 1800  # 30 minutes
        os.makedirs(cookie_dir, exist_ok=True)
        
    def get_cookie_file(self, email):
        """Get cookie file path for specific account"""
        safe_email = email.replace('@', '_at_').replace('.', '_dot_')
        return os.path.join(self.cookie_dir, f"linkedin_{safe_email}.pkl")
        
    def has_valid_cookies(self, email):
        """Check if account has saved cookies"""
        cookie_file = self.get_cookie_file(email)
        
        if not os.path.exists(cookie_file):
            return False
            
        # Check if cookies are fresh enough (< 24 hours old)
        cookie_age = time.time() - os.path.getmtime(cookie_file)
        return cookie_age < 86400  # 24 hours
        
    def save_session_cookies(self, email, cookies):
        """Save cookies for an account"""
        cookie_file = self.get_cookie_file(email)
        
        try:
            with open(cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            logger.info(f"Saved session cookies for {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies for {email}: {str(e)}")
            return False
            
    def load_session_cookies(self, email):
        """Load cookies for an account"""
        cookie_file = self.get_cookie_file(email)
        
        if not os.path.exists(cookie_file):
            logger.warning(f"No cookie file found for {email}")
            return None
            
        try:
            with open(cookie_file, 'rb') as f:
                cookies = pickle.load(f)
            logger.info(f"Loaded {len(cookies)} cookies for {email}")
            return cookies
        except Exception as e:
            logger.error(f"Failed to load cookies for {email}: {str(e)}")
            return None
            
    def rotate_session_if_needed(self):
        """Determine if we should rotate to a new session"""
        if time.time() - self.last_rotation > self.rotation_interval:
            logger.info("Session rotation interval reached")
            self.last_rotation = time.time()
            return True
        return False
        
    def mark_session_success(self, email):
        """Mark a session as successful"""
        if email not in self.session_health:
            self.session_health[email] = {"success": 0, "failure": 0}
        
        self.session_health[email]["success"] += 1
        
    def mark_session_failure(self, email):
        """Mark a session as failed"""
        if email not in self.session_health:
            self.session_health[email] = {"success": 0, "failure": 0}
        
        self.session_health[email]["failure"] += 1
        
    def get_session_health(self, email):
        """Get session health score (0-100)"""
        if email not in self.session_health:
            return 100  # New session starts with perfect score
            
        stats = self.session_health[email]
        total = stats["success"] + stats["failure"]
        
        if total == 0:
            return 100
            
        return int((stats["success"] / total) * 100)
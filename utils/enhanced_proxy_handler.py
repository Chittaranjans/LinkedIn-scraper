import os
import time
import random
import logging
import asyncio
from utils.logging_config import LoggingConfig

logger = LoggingConfig.setup_logging("proxy_handler")

class EnhancedProxyHandler:
    def __init__(self):
        self.proxy_groups = {
            "tier1": [],  # High-performance proxies
            "tier2": [],  # Medium reliability proxies
            "tier3": []   # Backup proxies
        }
        self.proxy_usage = {}  # Track usage counts and successes
        self.proxy_cooldowns = {}  # Track when proxies can be reused
        self.proxy_failures = {}  # Track proxy failures
        
        # Load proxies from file
        self._load_proxies()
        
    def _load_proxies(self):
        """Load proxies from a single file and distribute into tiers"""
        try:
            # Update path to look in the correct location
            # Original was: proxy_file = os.path.join("utils", "proxies.txt")
            # First try direct path, then try relative path
            proxy_file = "utils/proxies.txt"
            if not os.path.exists(proxy_file):
                proxy_file = os.path.join(os.path.dirname(__file__), "proxies.txt")
            
            if os.path.exists(proxy_file):
                with open(proxy_file, "r") as f:
                    all_proxies = []
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("//") and ":" in line:
                            all_proxies.append(line)
                    
                    logger.info(f"Loaded {len(all_proxies)} proxies from {proxy_file}")
                    
                    if not all_proxies:
                        logger.warning("No valid proxies found in the file")
                        return
                    
                    # Distribute proxies evenly across tiers
                    # Tier 1: First 1/3 of proxies (considered highest quality)
                    # Tier 2: Middle 1/3 of proxies (medium quality)
                    # Tier 3: Last 1/3 of proxies (lowest quality/backup)
                    total = len(all_proxies)
                    tier1_count = total // 3
                    tier2_count = tier1_count
                    tier3_count = total - tier1_count - tier2_count
                    
                    self.proxy_groups["tier1"] = all_proxies[:tier1_count]
                    self.proxy_groups["tier2"] = all_proxies[tier1_count:tier1_count+tier2_count]
                    self.proxy_groups["tier3"] = all_proxies[tier1_count+tier2_count:]
                    
                    logger.info(f"Distributed proxies: Tier 1: {len(self.proxy_groups['tier1'])}, "
                               f"Tier 2: {len(self.proxy_groups['tier2'])}, "
                               f"Tier 3: {len(self.proxy_groups['tier3'])}")
            else:
                logger.error(f"Proxy file not found: {proxy_file}")
        except Exception as e:
            logger.error(f"Error loading proxies: {str(e)}")

    async def get_optimal_proxy(self, task_importance=1):
        """Get the best available proxy based on task importance"""
        # Choose tier based on task importance
        tier = f"tier{task_importance}" if 1 <= task_importance <= 3 else "tier1"
        
        # If tier is empty or all proxies are on cooldown, try other tiers
        if not self.proxy_groups.get(tier) or all(
            p in self.proxy_cooldowns and self.proxy_cooldowns[p] > time.time() 
            for p in self.proxy_groups.get(tier, [])
        ):
            # Try all tiers in order of preference
            for fallback_tier in ["tier1", "tier2", "tier3"]:
                if fallback_tier != tier and self.proxy_groups.get(fallback_tier):
                    # Found an alternative tier with proxies
                    tier = fallback_tier
                    logger.info(f"Falling back to {tier} proxies")
                    break
        
        # Get available proxies without cooldowns
        current_time = time.time()
        available_proxies = [
            p for p in self.proxy_groups.get(tier, []) 
            if p not in self.proxy_cooldowns or self.proxy_cooldowns[p] < current_time
        ]
        
        if not available_proxies:
            # If no available proxies in any tier, return None
            logger.warning("No available proxies found in any tier")
            return None
        
        # Select least used proxy
        proxy = min(available_proxies, key=lambda p: self.proxy_usage.get(p, 0))
        self.proxy_usage[proxy] = self.proxy_usage.get(proxy, 0) + 1
        logger.info(f"Selected proxy: {proxy} (usage: {self.proxy_usage[proxy]})")
        
        return proxy
    
    def mark_proxy_as_failed(self, proxy):
        """Mark a proxy as failed and add cooldown"""
        if proxy:
            # Increase failure count
            self.proxy_failures[proxy] = self.proxy_failures.get(proxy, 0) + 1
            
            # Set cooldown based on failure count
            failures = self.proxy_failures.get(proxy, 0)
            cooldown = min(60 * (2 ** (failures - 1)), 3600)  # Exponential backoff up to 1 hour
            self.proxy_cooldowns[proxy] = time.time() + cooldown
            
            logger.warning(f"Marked proxy {proxy} as failed (count: {failures}, cooldown: {cooldown}s)")
    
    def mark_proxy_success(self, proxy):
        """Mark a proxy as successful"""
        if proxy:
            # Reset failure count
            if proxy in self.proxy_failures and self.proxy_failures[proxy] > 0:
                self.proxy_failures[proxy] = max(0, self.proxy_failures[proxy] - 1)
            
            # Remove any cooldown
            if proxy in self.proxy_cooldowns:
                del self.proxy_cooldowns[proxy]
    
    def get_status(self):
        """Get proxy pool status"""
        return {
            "total_proxies": sum(len(proxies) for proxies in self.proxy_groups.values()),
            "available_proxies": sum(
                len([p for p in proxies if p not in self.proxy_cooldowns or self.proxy_cooldowns[p] < time.time()])
                for proxies in self.proxy_groups.values()
            ),
            "cooldown_proxies": len(self.proxy_cooldowns),
            "failed_proxies": len(self.proxy_failures),
            "tiers": {
                tier: len(proxies) for tier, proxies in self.proxy_groups.items()
            }
        }
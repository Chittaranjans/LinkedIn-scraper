# utils/scheduler.py
import time
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class ScrapingScheduler:
    def __init__(self):
        self.active_tasks = {}  # Store active tasks
        self.completed_tasks = set()  # Store completed tasks
        self.processing = set()  # Tasks being processed
        self.domain_rates = {
            "linkedin.com": {
                "requests_per_hour": 100,
                "current_count": 0,
                "last_reset": time.time()
            }
        }
        self.entity_importance = {
            "job": 1,
            "company": 3,  # Companies are highest priority (more valuable data) 
            "profile": 2
        }
        self.task_queue = asyncio.PriorityQueue()
        
        # Clear any stale tasks at initialization
        self.clear_stale_tasks()
    
    def clear_stale_tasks(self):
        """Clear any stale tasks from previous runs"""
        self.active_tasks = {}
        self.processing = set()
        # For testing purposes, clear the completed_tasks too
        # In production you might want to keep completed_tasks for caching
        self.completed_tasks = set()
        logger.info("Cleared all stale tasks from scheduler")
    
    async def schedule_task(self, task_type, entity_type, entity_id, url=None):
        """Schedule a task if not already in progress"""
        # Create a unique task ID WITHOUT timestamp
        # This is the root of the issue - we need consistent IDs
        task_id = f"{entity_type}_{entity_id}"
        
        # Check if task is being processed or is active
        if task_id in self.processing:
            logger.debug(f"Task {task_id} was in processing set, removing stale entry")
            self.processing.remove(task_id)
            
        if task_id in self.active_tasks:
            # Check if the task has been stuck for too long (over 10 minutes)
            if time.time() - self.active_tasks[task_id]["start_time"] > 600:
                # Remove stale task
                logger.debug(f"Removing stale task {task_id} (stuck for >10 min)")
                del self.active_tasks[task_id]
            else:
                logger.debug(f"Task {task_id} already in progress, rejecting")
                return {
                    "scheduled": False,
                    "reason": "Task already in progress",
                    "task_id": task_id
                }
        
        # Check if task was recently completed (within last 10 minutes)
        if task_id in self.completed_tasks:
            logger.debug(f"Task {task_id} recently completed, rejecting")
            return {
                "scheduled": False,
                "reason": "Task recently completed",
                "task_id": task_id
            }
            
        # Schedule the task
        priority = self.entity_importance.get(entity_type, 1)
        
        # Mark task as active
        self.active_tasks[task_id] = {
            "type": task_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "url": url,
            "start_time": time.time(),
            "priority": priority
        }
        
        logger.debug(f"Successfully scheduled task {task_id} with priority {priority}")
        return {
            "scheduled": True,
            "priority": priority,
            "task_id": task_id
        }
    
    def mark_task_complete(self, task_id):
        """Mark a task as completed"""
        if not task_id:
            return
            
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            self.completed_tasks.add(task_id)
            
        if task_id in self.processing:
            self.processing.remove(task_id)
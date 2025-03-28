import time
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
import logging

logger = logging.getLogger("app.middleware")

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limits request rate per IP address"""
    def __init__(self, app):
        super().__init__(app)
        self.rate_limit = settings.RATE_LIMIT
        self.requests = {}  # dict to store IP: [timestamp1, timestamp2, ...]
        self.window = 60  # window in seconds
    
    async def dispatch(self, request: Request, call_next):
        # Get IP address
        ip = request.client.host
        current_time = time.time()
        
        # Clean up old requests
        if ip in self.requests:
            self.requests[ip] = [t for t in self.requests[ip] if current_time - t < self.window]
        else:
            self.requests[ip] = []
        
        # Check if rate limit is exceeded
        if len(self.requests[ip]) >= self.rate_limit:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Add current request
        self.requests[ip].append(current_time)
        
        # Process the request
        return await call_next(request)
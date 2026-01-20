"""
HTTP utilities for making requests
"""
import requests
from typing import Optional
from config import settings


class HTTPSession:
    """Manages HTTP session with proper headers and configuration"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(settings.DEFAULT_HEADERS)
    
    def get(self, url: str, timeout: Optional[int] = None) -> requests.Response:
        """
        Make a GET request
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            Response object
        """
        if timeout is None:
            timeout = settings.REQUEST_TIMEOUT
        
        return self.session.get(url, timeout=timeout, allow_redirects=True)
    
    def close(self):
        """Close the session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
"""
Base scraper class with common functionality
"""
from abc import ABC, abstractmethod
from typing import List
from src.utils.http_utils import HTTPSession


class BaseScraper(ABC):
    """Abstract base class for scrapers"""
    
    def __init__(self):
        self.http_session = HTTPSession()
    
    @abstractmethod
    def get_document_list(self, page: int = 0) -> List[dict]:
        """
        Fetch list of documents
        
        Args:
            page: Page offset
            
        Returns:
            List of document metadata
        """
        pass
    
    @abstractmethod
    def download_document(self, document_path: str, title: str) -> tuple:
        """
        Download a document
        
        Args:
            document_path: Path to document
            title: Document title
            
        Returns:
            Tuple of (content, local_path)
        """
        pass
    
    def close(self):
        """Clean up resources"""
        self.http_session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
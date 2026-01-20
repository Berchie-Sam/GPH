"""
Data models for Hansard documents
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Hansard:
    """Represents a Parliament Hansard document"""
    title: str
    pdf_path: str
    date: str
    pdf_content: Optional[bytes] = None
    text_content: Optional[str] = None
    local_pdf_path: Optional[str] = None
    local_txt_path: Optional[str] = None
    
    def __str__(self):
        return f"Hansard({self.date} - {self.title})"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'title': self.title,
            'pdf_path': self.pdf_path,
            'date': self.date,
            'local_pdf_path': self.local_pdf_path,
            'local_txt_path': self.local_txt_path
        }
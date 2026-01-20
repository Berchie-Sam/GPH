"""
PDF parsing utilities
"""
import io
import PyPDF2
from typing import Optional


class PDFParser:
    """Handles PDF text extraction"""
    
    @staticmethod
    def extract_text(pdf_content: bytes) -> Optional[str]:
        """
        Extract text from PDF bytes
        
        Args:
            pdf_content: PDF file as bytes
            
        Returns:
            Extracted text or None if extraction fails
        """
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text += f"\n--- Page {page_num} ---\n"
                text += page.extract_text()
            
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return None
    
    @staticmethod
    def is_valid_pdf(content: bytes) -> bool:
        """
        Check if content is a valid PDF
        
        Args:
            content: File content as bytes
            
        Returns:
            True if valid PDF
        """
        return content[:4] == b'%PDF'
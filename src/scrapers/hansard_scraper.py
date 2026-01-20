"""
Ghana Parliament Hansard Scraper
"""
import re
import time
from typing import List, Optional, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from config import settings
from src.scrapers.base_scraper import BaseScraper
from src.models.hansard import Hansard
from src.parsers.pdf_parser import PDFParser
from src.utils import file_utils


class HansardScraper(BaseScraper):
    """Scraper for Ghana Parliament Hansard documents"""
    
    def __init__(self):
        super().__init__()
        self.pdf_parser = PDFParser()
    
    def get_document_list(self, page: int = 0) -> List[Hansard]:
        """
        Fetch list of available hansards from a specific page
        
        Args:
            page: Page offset (0, 50, 100, etc.)
            
        Returns:
            List of Hansard objects
        """
        url = f"{settings.DOCS_URL}&offset={page}"
        
        try:
            response = self.http_session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            hansards = []
            rows = soup.find_all('tr', attrs={'role': 'button'})
            
            for row in rows:
                try:
                    onclick = row.get('onclick', '')
                    # Extract PDF path from onclick="showPDF('pb/12th December, 2025.pdf','Hansard...')"
                    match = re.search(r"showPDF\('([^']+)','([^']+)'\)", onclick)
                    if match:
                        pdf_path = match.group(1).strip()
                        title = match.group(2).strip()
                        
                        # Get date from first column
                        cells = row.find_all('td')
                        if cells:
                            date_text = cells[0].get_text(strip=True)
                            # Extract just the date part
                            date_match = re.search(
                                r'([A-Za-z]+,\s+\d+(?:st|nd|rd|th)\s+[A-Za-z]+,\s+\d{4})',
                                date_text
                            )
                            if date_match:
                                date_text = date_match.group(1)
                        else:
                            date_text = "Unknown"
                        
                        hansards.append(Hansard(
                            title=title,
                            pdf_path=pdf_path,
                            date=date_text
                        ))
                except Exception as e:
                    print(f"Warning: Error processing row: {e}")
                    continue
            
            return hansards
        except Exception as e:
            print(f"Error fetching hansard list: {e}")
            return []
    
    def download_document(self, pdf_path: str, title: str) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Download a hansard PDF
        
        Args:
            pdf_path: Path to PDF on server
            title: Document title
            
        Returns:
            Tuple of (pdf_content, local_path)
        """
        print(f"\n📥 Attempting to download: {title}")
        print(f"   PDF path from HTML: {pdf_path}")
        
        # Construct the full URL
        pdf_url = urljoin(settings.PDF_BASE_URL, pdf_path)
        print(f"   Trying URL: {pdf_url}")
        
        try:
            response = self.http_session.get(pdf_url)
            
            if response.status_code == 200:
                # Verify it's actually a PDF
                if self.pdf_parser.is_valid_pdf(response.content):
                    print(f"   ✅ Successfully downloaded PDF ({len(response.content)} bytes)")
                    
                    # Save the PDF
                    local_path = file_utils.save_pdf(
                        response.content,
                        title,
                        settings.PDF_DIR
                    )
                    
                    print(f"   💾 Saved to: {local_path}")
                    return response.content, local_path
                else:
                    print(f"   ❌ Response is not a valid PDF")
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.reason}")
        
        except Exception as e:
            print(f"   ❌ Error downloading PDF: {e}")
        
        return None, None
    
    def find_hansard(self, date_str: str) -> Optional[Hansard]:
        """
        Search for a specific hansard by date
        
        Args:
            date_str: Date string to search for (e.g., '12th December, 2025')
            
        Returns:
            Hansard object if found, None otherwise
        """
        print(f"🔍 Searching for hansard: {date_str}")
        
        # Search through pages
        for page in range(0, settings.MAX_PAGES_TO_SEARCH * settings.RECORDS_PER_PAGE, settings.RECORDS_PER_PAGE):
            print(f"   Checking page {page//settings.RECORDS_PER_PAGE + 1}...")
            hansards = self.get_document_list(page)
            
            for h in hansards:
                if date_str.lower() in h.date.lower() or date_str.lower() in h.title.lower():
                    return h
            
            if not hansards:  # No more pages
                break
        
        return None
    
    def download_and_extract(self, hansard: Hansard) -> Optional[Hansard]:
        """
        Download a hansard and extract its text
        
        Args:
            hansard: Hansard object to download
            
        Returns:
            Updated Hansard object with content, or None if failed
        """
        # Download PDF
        pdf_content, pdf_path = self.download_document(hansard.pdf_path, hansard.title)
        
        if not pdf_content or not pdf_path:
            return None
        
        hansard.pdf_content = pdf_content
        hansard.local_pdf_path = pdf_path
        
        # Extract text
        print("\n📝 Extracting text from PDF...")
        text = self.pdf_parser.extract_text(pdf_content)
        
        if text:
            hansard.text_content = text
            
            # Save text file
            metadata = {
                'Title': hansard.title,
                'Date': hansard.date,
                'PDF Path': hansard.pdf_path
            }
            
            text_path = file_utils.save_text(
                text,
                hansard.title,
                settings.TXT_DIR,
                metadata
            )
            
            hansard.local_txt_path = text_path
            print(f"   ✅ Saved text to: {text_path}")
        
        return hansard
    
    def bulk_download(self, start_page: int = 0, num_pages: int = 1) -> Tuple[List[Hansard], List[Hansard]]:
        """
        Download multiple hansards
        
        Args:
            start_page: Starting page number (0, 1, 2, etc.)
            num_pages: Number of pages to download
            
        Returns:
            Tuple of (downloaded_list, failed_list)
        """
        downloaded = []
        failed = []
        
        for page_num in range(start_page, start_page + num_pages):
            page_offset = page_num * settings.RECORDS_PER_PAGE
            
            print(f"\n{'='*80}")
            print(f"📄 FETCHING PAGE {page_num + 1}")
            print(f"{'='*80}")
            
            hansards = self.get_document_list(page_offset)
            
            if not hansards:
                print("No more hansards found")
                break
            
            print(f"Found {len(hansards)} hansards on this page\n")
            
            for idx, hansard in enumerate(hansards, 1):
                print(f"\n[{idx}/{len(hansards)}] Processing: {hansard.title}")
                
                # Check if already downloaded
                if file_utils.file_exists(hansard.title, settings.PDF_DIR):
                    print(f"   ⏭️ Already exists")
                    downloaded.append(hansard)
                    continue
                
                # Download and extract
                result = self.download_and_extract(hansard)
                
                if result:
                    downloaded.append(result)
                else:
                    failed.append(hansard)
                
                # Be respectful - add delay
                time.sleep(settings.DELAY_BETWEEN_REQUESTS)
        
        # Summary
        print(f"\n{'='*80}")
        print(f"📊 DOWNLOAD SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Successfully downloaded: {len(downloaded)}")
        print(f"❌ Failed: {len(failed)}")
        
        if failed:
            print("\nFailed downloads:")
            for h in failed:
                print(f"   - {h.title} ({h.pdf_path})")
        
        return downloaded, failed
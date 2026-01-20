"""
Configuration settings for Ghana Parliament Hansard Scraper
"""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Parliament website URLs
PARLIAMENT_BASE_URL = "https://www.parliament.gh"
DOCS_URL = f"{PARLIAMENT_BASE_URL}/docs?type=HS"
PDF_BASE_URL = f"{PARLIAMENT_BASE_URL}/epanel/docs/"

# Download settings
DOWNLOAD_DIR = DATA_DIR / "hansards"
PDF_DIR = DOWNLOAD_DIR / "pdf"
TXT_DIR = DOWNLOAD_DIR / "txt"

# Create download directories
PDF_DIR.mkdir(parents=True, exist_ok=True)
TXT_DIR.mkdir(parents=True, exist_ok=True)

# HTTP settings
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 30  # seconds
RETRY_ATTEMPTS = 3
DELAY_BETWEEN_REQUESTS = 2  # seconds

# Scraping settings
RECORDS_PER_PAGE = 50
MAX_PAGES_TO_SEARCH = 10

# HTTP Headers
DEFAULT_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': DOCS_URL
}

# Logging
LOG_FILE = LOG_DIR / "scraper.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
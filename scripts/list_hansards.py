"""
Script to list available hansards
Usage: python scripts/list_hansards.py [page_number]
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrapers.hansard_scraper import HansardScraper


def main():
    page = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    
    print("="*80)
    print("🏛️  AVAILABLE HANSARDS")
    print("="*80)
    
    with HansardScraper() as scraper:
        hansards = scraper.get_document_list(page)
        
        if not hansards:
            print("No hansards found")
            return
        
        print(f"\nFound {len(hansards)} hansards on page {page + 1}:\n")
        
        for i, h in enumerate(hansards, 1):
            print(f"{i:2d}. {h.date:30s} - {h.title}")


if __name__ == "__main__":
    main()

"""
Script to download a single hansard by date
Usage: python scripts/download_single.py "12th December, 2025"
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrapers.hansard_scraper import HansardScraper


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/download_single.py \"<date>\"")
        print("Example: python scripts/download_single.py \"12th December, 2025\"")
        sys.exit(1)
    
    date_str = sys.argv[1]
    
    print("="*80)
    print("🏛️  GHANA PARLIAMENT HANSARD SCRAPER")
    print("="*80)
    
    with HansardScraper() as scraper:
        # Find the hansard
        hansard = scraper.find_hansard(date_str)
        
        if not hansard:
            print(f"\n❌ Hansard not found for: {date_str}")
            sys.exit(1)
        
        print(f"\n✅ Found hansard:")
        print(f"   Title: {hansard.title}")
        print(f"   Date: {hansard.date}")
        print(f"   PDF Path: {hansard.pdf_path}")
        
        # Download and extract
        result = scraper.download_and_extract(hansard)
        
        if result:
            print("\n" + "="*80)
            print("✅ SUCCESS!")
            print("="*80)
            print(f"PDF saved to: {result.local_pdf_path}")
            print(f"Text saved to: {result.local_txt_path}")
            
            if result.text_content:
                print(f"\nFirst 500 characters of extracted text:")
                print("-" * 80)
                print(result.text_content[:500])
                print("-" * 80)
        else:
            print("\n❌ Failed to download hansard")
            sys.exit(1)


if __name__ == "__main__":
    main()
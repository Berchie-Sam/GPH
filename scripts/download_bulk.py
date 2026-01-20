"""
Script to bulk download hansards
Usage: python scripts/download_bulk.py [start_page] [num_pages]
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrapers.hansard_scraper import HansardScraper


def main():
    # Parse command line arguments
    start_page = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    num_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    print("="*80)
    print("🏛️  GHANA PARLIAMENT HANSARD SCRAPER - BULK DOWNLOAD")
    print("="*80)
    print(f"Starting from page: {start_page + 1}")
    print(f"Number of pages: {num_pages}")
    print(f"Total hansards to process: ~{num_pages * 50}")
    print("="*80)
    
    with HansardScraper() as scraper:
        downloaded, failed = scraper.bulk_download(
            start_page=start_page,
            num_pages=num_pages
        )
        
        # Final summary
        print("\n" + "="*80)
        print("📊 FINAL SUMMARY")
        print("="*80)
        print(f"✅ Total downloaded: {len(downloaded)}")
        print(f"❌ Total failed: {len(failed)}")
        
        if downloaded:
            print(f"\n✅ Successfully downloaded hansards:")
            for h in downloaded[:10]:  # Show first 10
                print(f"   - {h.date}: {h.title}")
            if len(downloaded) > 10:
                print(f"   ... and {len(downloaded) - 10} more")


if __name__ == "__main__":
    main()
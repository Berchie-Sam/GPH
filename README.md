# Ghana Parliamentary Hansard Data Scraper

A modular Python tool to download and extract text from Ghana Parliament Hansard documents.

## Features

- 📥 Download individual or bulk hansard PDFs
- 📝 Automatic text extraction from PDFs
- 🗂️ Organized file structure (separate PDF and TXT folders)
- 🔍 Search hansards by date
- ⚡ Configurable settings
- 🧩 Modular, maintainable code structure

## Project Structure

```
GPH/
├── config/
│   └── settings.py          # Configuration settings
├── src/
│   ├── models/
│   │   └── hansard.py       # Data models
│   ├── parsers/
│   │   └── pdf_parser.py    # PDF text extraction
│   ├── scrapers/
│   │   ├── base_scraper.py  # Base scraper class
│   │   └── hansard_scraper.py # Main scraper
│   └── utils/
│       ├── file_utils.py    # File operations
│       └── http_utils.py    # HTTP utilities
├── scripts/
│   ├── download_single.py   # Download single hansard
│   ├── download_bulk.py     # Bulk download
│   └── list_hansards.py     # List available hansards
├── data/
│   └── hansards/
│       ├── pdf/             # Downloaded PDFs
│       └── txt/             # Extracted text
└── requirements.txt
```

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd GPH
```

2. Create a virtual environment:
```bash
python -m venv rgtenv
source rgtenv/bin/activate  # On Windows: rgtenv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### List Available Hansards

```bash
python scripts/list_hansards.py [page_number]
```

Example:
```bash
python scripts/list_hansards.py 0  # List first page
```

### Download Single Hansard

```bash
python scripts/download_single.py "<date>"
```

Example:
```bash
python scripts/download_single.py "12th December, 2025"
```

### Bulk Download

```bash
python scripts/download_bulk.py [start_page] [num_pages]
```

Examples:
```bash
# Download first 2 pages (100 hansards)
python scripts/download_bulk.py 0 2

# Download pages 5-7 (150 hansards)
python scripts/download_bulk.py 5 3
```

## Configuration

Edit `config/settings.py` to customize:
- Download directories
- HTTP timeout and retry settings
- Pagination settings
- Request delays

## Output

Files are organized as:
```
data/hansards/
├── pdf/
│   ├── Hansard_12th_December_2025.pdf
│   └── ...
└── txt/
    ├── Hansard_12th_December_2025.txt
    └── ...
```

Each text file includes:
- Document metadata (title, date, PDF path)
- Extracted text content with page markers

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Code Structure

- **Models**: Data structures (`Hansard` class)
- **Scrapers**: Web scraping logic
- **Parsers**: Document processing (PDF text extraction)
- **Utils**: Helper functions (HTTP, file operations)
- **Scripts**: Command-line interfaces

## License

MIT License

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Acknowledgments

Data source: [Ghana Parliament Official Website](https://www.parliament.gh)
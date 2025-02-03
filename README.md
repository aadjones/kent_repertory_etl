# Kent Repertory ETL

This project converts the static, hierarchical, hyperlink-based content of the Kent repertory webpage into a normalized relational database schema.

## Overview
- **Scraping:** Fetch and parse HTML content using Python (Requests + BeautifulSoup).
- **Transformation:** Clean and organize data into structured formats.
- **Database Loading:** Insert structured data into PostgreSQL.

## Directory Structure
- `src/` - Source code for scraping, transformation, and loading.
- `data/` - Stores raw and processed data.
- `docs/` - Documentation for the project.
- `tests/` - Unit tests for the modules.

## Setup
1. Create and activate a virtual environment:
   ```bash
   python -m venv myenv
   source myenv/bin/activate

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

1. Run the scraper to fetch and parse the HTML content:
   ```bash
   python src/scraper.py
   ```

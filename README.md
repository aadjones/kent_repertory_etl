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
1. From the project root, run
   ```bash
   make
   ```
   Then, activate the virtual environment.
   ```
   # On macOS/Linux:
   source env/bin/activate
   # On Windows:
   .\env\Scripts\activate
   ```
   
1. Run the scraper to fetch and parse the HTML content:
   ```bash
   python src/scraper.py
   ```

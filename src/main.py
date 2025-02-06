import logging
import os
import sys

from extractor import extract_source
from loader import load_chapter
from logging_setup import setup_logging
from transformer import transform_html_to_chapter

# Set up logging as early as possible
setup_logging()

logger = logging.getLogger(__name__)
logger.info("Starting the ETL process.")


def main():
    if len(sys.argv) > 1:
        url = sys.argv[1]
        logging.info(f"Fetching HTML from URL: {url}")
        try:
            html_content = extract_source(url=url)
        except Exception as e:
            logging.error(f"Error fetching the page: {e}")
            sys.exit(1)
    else:
        local_path = os.path.join("data", "raw", "kent0000_P1.html")
        logging.info(f"No URL provided. Using local file: {local_path}")
        html_content = extract_source(local_path=local_path)

    page_info = {"pages_covered": "p. 1-5"}
    chapter_entity = transform_html_to_chapter(html_content, page_info)
    load_chapter(chapter_entity)


if __name__ == "__main__":
    main()

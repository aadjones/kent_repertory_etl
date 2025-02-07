import logging
import os
import sys

from extractor import extract_source
from loader import load_chapter
from logging_setup import setup_logging
from text_utils import compute_page_range
from transformer import transform_html_to_chapter

# Set up logging as early as possible
setup_logging()

logger = logging.getLogger(__name__)
logger.info("Starting the ETL process.")


def main():
    # Get the Kent file identifier from the command line (e.g., "0000", "0005", etc.)
    if len(sys.argv) > 1:
        kent_identifier = sys.argv[1]
        logger.info(f"Processing Kent file identifier: {kent_identifier}")
    else:
        kent_identifier = "0000"
        logger.info(f"No Kent identifier provided. Defaulting to: {kent_identifier}")

    # Compute the starting page from the identifier.
    start_page = int(kent_identifier) + 1
    local_path = os.path.join("data", "raw", f"kent{kent_identifier}_P{start_page}.html")
    logger.info(f"Using local file: {local_path}")

    # Compute the page range for page_info.
    page_info = compute_page_range(kent_identifier)

    html_content = extract_source(local_path=local_path)
    chapter_entity = transform_html_to_chapter(html_content, page_info)
    load_chapter(chapter_entity)


if __name__ == "__main__":
    main()

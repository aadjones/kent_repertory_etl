import logging
import os
import sys

from bs4 import BeautifulSoup

from scraper_utils import (
    fetch_html,
    group_by_page,
    is_decorative,
    load_local_html,
    parse_directory,
    parse_remedy_list,
    save_chapter,
)

# Configure the root logger.
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


def parse_chapter(html, page_info=None):
    """
    Parse the HTML of a single Kent page (covering a subject like MIND spanning multiple pages)
    into a Chapter entity.

    We assume the HTML belongs to one subject (e.g., MIND) and includes multiple
    page boundaries (e.g., "MIND p. 1", "MIND p. 2", etc.). The content between boundaries
    are the rubrics that belong to that page.

    Returns a dictionary with keys:
      - title: from the <title> tag
      - subject: overall subject (e.g., "MIND")
      - pages: list of page groups, each with a "page" marker (e.g., "P1") and a list of rubrics.
    """
    soup = BeautifulSoup(html, "lxml")
    chapter = {}

    title_tag = soup.find("title")
    chapter_title = title_tag.get_text(strip=True) if title_tag else "No title found"
    chapter["title"] = chapter_title
    logging.info(f"Chapter title: {chapter_title}")
    if page_info:
        chapter["page_info"] = page_info

    # Parse rubrics: try nested <dir> tags; fallback to <p> tags.
    if soup.find("dir"):
        rubrics = parse_directory(soup.find("dir"))
        logging.debug(f"Parsed {len(rubrics)} rubrics using nested <dir>.")
    else:
        rubrics = []
        paragraphs = soup.find_all("p")
        current_rubric = None
        for p in paragraphs:
            raw = p.decode_contents()
            if is_decorative(raw):
                continue
            if ":" in raw:
                header_raw, remedy_raw = raw.split(":", 1)
                header = BeautifulSoup(header_raw, "lxml").get_text(strip=True)
                description = BeautifulSoup(remedy_raw, "lxml").get_text(" ", strip=True)
                remedies = parse_remedy_list(remedy_raw)
                current_rubric = {
                    "title": header.strip(),
                    "description": description.strip(),
                    "remedies": remedies,
                    "subrubrics": [],
                }
            else:
                header = BeautifulSoup(raw, "lxml").get_text(strip=True)
                current_rubric = {"title": header.strip(), "description": "", "remedies": [], "subrubrics": []}
            if current_rubric:
                rubrics.append(current_rubric)
        logging.debug(f"Parsed {len(rubrics)} rubrics using <p> tags.")

    # Group rubrics into page boundaries using subject markers like "MIND p. 1".
    pages = group_by_page(rubrics, subject_keyword="MIND")
    logging.info(f"Grouped rubrics into {len(pages)} pages.")
    chapter["pages"] = pages
    chapter["subject"] = "MIND"
    return chapter


def main():
    """
    Main entry point.

    Usage:
      - If a command line argument is provided, it is taken as the URL to fetch.
      - Otherwise, the script falls back to a local HTML file (data/raw/kent0000_P1.html).

    The resulting chapter entity is saved as a JSON file in data/processed/.
    """
    if len(sys.argv) > 1:
        url = sys.argv[1]
        logging.info(f"Fetching HTML from URL: {url}")
        try:
            html_content = fetch_html(url)
        except Exception as e:
            logging.error(f"Error fetching the page: {e}")
            sys.exit(1)
    else:
        local_path = os.path.join("data", "raw", "kent0000_P1.html")
        logging.info(f"No URL provided. Using local file: {local_path}")
        html_content = load_local_html(local_path)

    page_info = {"pages_covered": "p. 1-5"}
    chapter_entity = parse_chapter(html_content, page_info)
    save_chapter(chapter_entity)


if __name__ == "__main__":
    main()

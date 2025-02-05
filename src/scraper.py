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
    Parse the HTML of a single Kent page into a Chapter entity.

    If nested <dir> tags exist, use them; otherwise, use <p> tags.
    This function groups rubrics into pages using subject boundary markers.

    Returns a dictionary with keys:
      - title: from the <title> tag
      - subject: overall subject (extracted from boundaries)
      - pages: list of page groups (each with "page" and "rubrics")
      - (optional) page_info: metadata about pages covered.
    """

    soup = BeautifulSoup(html, "lxml")
    chapter = {}

    title_tag = soup.find("title")
    chapter_title = title_tag.get_text(strip=True) if title_tag else "No title found"
    chapter["title"] = chapter_title
    if page_info:
        chapter["page_info"] = page_info

    rubrics = []
    if soup.find("dir"):
        rubrics = parse_directory(soup.find("dir"))
    else:
        paragraphs = soup.find_all("p")
        current_rubric = None
        for p in paragraphs:
            raw = p.decode_contents()
            if is_decorative(raw):
                continue
            if ":" in raw:
                header_raw, remedy_raw = raw.split(":", 1)
                header = BeautifulSoup(header_raw, "lxml").get_text(strip=True)
                header = header.replace(":", "").strip()
                description = BeautifulSoup(remedy_raw, "lxml").get_text(" ", strip=True)
                description = description.replace(":", "").strip()
                remedies = parse_remedy_list(remedy_raw)
                current_rubric = {"title": header, "description": description, "remedies": remedies, "subrubrics": []}
                rubrics.append(current_rubric)
            else:
                text = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
                text = text.replace(":", "").strip()
                if current_rubric:
                    current_rubric["description"] += " " + text
                else:
                    current_rubric = {"title": text, "description": "", "remedies": [], "subrubrics": []}
                    rubrics.append(current_rubric)
    # Group rubrics into pages.
    pages = group_by_page(rubrics, subject_keyword="MIND")
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

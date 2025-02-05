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

from transformer_utils import transform_content

# Configure the root logger.
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


def parse_chapter(html, page_info=None):
    """
    Parse the HTML of a single Kent page (covering a subject spanning multiple pages)
    into a Chapter entity.

    The resulting dictionary has the following keys:
      - title: extracted from the <title> tag
      - subject: overall subject (set to "MIND" by default, can be dynamically extracted later)
      - pages: a list of page groups. Each page group is a dictionary with:
          - page: a page marker (e.g., "P1")
          - content: a list of rubric dictionaries, each with:
                - rubric: the rubric title
                - remedies: a list of remedy dictionaries
                - (optionally) subcontent: list of nested rubric dictionaries
      - page_info: additional metadata (if provided)

    Note: This function uses nested <dir> tags if present; otherwise it falls back to parsing <p> tags.
    """
    from bs4 import BeautifulSoup
    import re

    soup = BeautifulSoup(html, "lxml")
    chapter = {}

    # Extract chapter title from <title>.
    title_tag = soup.find("title")
    chapter_title = title_tag.get_text(strip=True) if title_tag else "No title found"
    chapter["title"] = chapter_title
    if page_info:
        chapter["page_info"] = page_info

    # Parse rubrics using nested <dir> if available; else fallback to <p> tags.
    if soup.find("dir"):
        rubrics = parse_directory(soup.find("dir"))
    else:
        rubrics = []
        paragraphs = soup.find_all("p")
        current_rubric = None
        boundary_pattern = re.compile(r'^MIND\s*p\.?\s*\d+', re.IGNORECASE)
        for p in paragraphs:
            raw = p.decode_contents()
            if is_decorative(raw):
                continue
            # Use BeautifulSoup to extract plain text.
            full_text = BeautifulSoup(raw, "lxml").get_text(strip=True)
            if p.find("b"):
                # If this is a boundary marker, we leave it unsplit.
                if boundary_pattern.match(full_text):
                    header = full_text.replace(":", "").strip()
                    current_rubric = {
                        "title": header,
                        "description": "",
                        "remedies": [],
                        "subrubrics": []
                    }
                else:
                    if ":" in raw:
                        header_raw, remedy_raw = raw.split(":", 1)
                        header = BeautifulSoup(header_raw, "lxml").get_text(strip=True)
                        header = header.replace(":", "").strip()
                        description = BeautifulSoup(remedy_raw, "lxml").get_text(" ", strip=True)
                        description = description.replace(":", "").strip()
                        remedies = parse_remedy_list(remedy_raw)
                        current_rubric = {
                            "title": header,
                            "description": description,
                            "remedies": remedies,
                            "subrubrics": []
                        }
                    else:
                        header = full_text.replace(":", "").strip()
                        current_rubric = {
                            "title": header,
                            "description": "",
                            "remedies": [],
                            "subrubrics": []
                        }
            else:
                additional = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
                additional = additional.replace(":", "").strip()
                if current_rubric:
                    current_rubric["description"] += " " + additional
                else:
                    current_rubric = {
                        "title": additional,
                        "description": "",
                        "remedies": [],
                        "subrubrics": []
                    }
            if current_rubric:
                rubrics.append(current_rubric)

    # Group the flat list of rubrics into page boundaries using subject markers.
    pages = group_by_page(rubrics, subject_keyword="MIND")
    # Transform each page's rubrics into the final schema:
    # rename "rubrics" to "content", rename "title" to "rubric", drop "description",
    # and rename nested "subrubrics" to "subcontent".
    for page in pages:
        page["content"] = transform_content(page.pop("rubrics"))
    chapter["pages"] = pages
    chapter["subject"] = "MIND"  # (or dynamically extract if needed)
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

import logging
import os
import sys

from bs4 import BeautifulSoup

from scraper_utils import (
    extract_section_from_raw,
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
    Parse the HTML of a single Kent page (covering a section spanning 5 pages)
    into a Chapter entity.

    Output schema:
      - title: from <title> tag
      - section: dynamically extracted (e.g., "MIND", "VERTIGO", etc.)
      - pages: a list of page groups, each with:
           - page: page marker (e.g., "P100", "P101", etc.)
           - content: a list of rubric dictionaries, where each dictionary has:
                 - rubric: rubric title (without colons)
                 - remedies: list of remedy dictionaries
                 - (optionally) subcontent: nested rubric dictionaries
      - page_info: additional metadata (if provided)

    Any rubric with the title "KENT" (ignoring case) is filtered out.
    """
    import re

    soup = BeautifulSoup(html, "lxml")
    chapter = {}

    # Extract chapter title.
    title_tag = soup.find("title")
    chapter_title = title_tag.get_text(strip=True) if title_tag else "No title found"
    chapter["title"] = chapter_title
    if page_info:
        chapter["page_info"] = page_info

    # Extract section from raw HTML BEFORE filtering decorative content.
    section = extract_section_from_raw(html)
    if not section:
        section = "UNKNOWN"

    # Parse rubrics.
    if soup.find("dir"):
        rubrics = parse_directory(soup.find("dir"))
    else:
        rubrics = []
        paragraphs = soup.find_all("p")
        current_rubric = None
        # Use a boundary pattern that looks for a "p." marker.
        boundary_pattern = re.compile(r".*\bp\.?\s*\d+", re.IGNORECASE)
        for p in paragraphs:
            raw = p.decode_contents()
            if is_decorative(raw):
                continue
            full_text = BeautifulSoup(raw, "lxml").get_text(strip=True)
            if p.find("b"):
                if boundary_pattern.match(full_text):
                    # This is a boundary marker.
                    header = full_text.replace(":", "").strip()
                    current_rubric = {"title": header, "description": "", "remedies": [], "subrubrics": []}
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
                            "subrubrics": [],
                        }
                    else:
                        header = full_text.replace(":", "").strip()
                        current_rubric = {"title": header, "description": "", "remedies": [], "subrubrics": []}
            else:
                additional = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
                additional = additional.replace(":", "").strip()
                if current_rubric:
                    current_rubric["description"] += " " + additional
                else:
                    current_rubric = {"title": additional, "description": "", "remedies": [], "subrubrics": []}
            if current_rubric:
                rubrics.append(current_rubric)

    # Filter out any rubric with title "KENT".
    rubrics = [r for r in rubrics if r.get("title", "").strip().upper() != "KENT"]

    # (Optional) If a parsed section is available from rubrics, update section.
    # parsed_section = extract_section(rubrics)
    # if parsed_section != "UNKNOWN":
    #     section = parsed_section

    # Group rubrics into pages using the section as the subject keyword.
    pages = group_by_page(rubrics, subject_keyword=section)
    for page in pages:
        page["content"] = transform_content(page.pop("rubrics"))
    chapter["pages"] = pages
    chapter["section"] = section
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

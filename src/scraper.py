import os
import sys

from bs4 import BeautifulSoup

from scraper_utils import (
    fetch_html,
    group_by_page,
    is_decorative,
    load_local_html,
    parse_directory,
    remove_parentheses,
    save_chapter,
)


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
    if page_info:
        chapter["page_info"] = page_info

    # Parse rubrics: try using nested <dir> tags first; fallback to <p> tags.
    if soup.find("dir"):
        rubrics = parse_directory(soup.find("dir"))
    else:
        rubrics = []
        paragraphs = soup.find_all("p")
        current_rubric = None
        for p in paragraphs:
            text = p.get_text(" ", strip=True)
            if is_decorative(text):
                continue
            text = remove_parentheses(text)
            if p.find("b"):
                if current_rubric:
                    rubrics.append(current_rubric)
                if ":" in text:
                    header, remedy_text = text.split(":", 1)
                else:
                    header = text
                    remedy_text = ""
                current_rubric = {
                    "title": header.strip(),
                    "description": remedy_text.strip(),
                    "remedies": [r.strip() for r in remedy_text.split(",") if r.strip()],
                    "subrubrics": [],
                }
            else:
                if current_rubric:
                    current_rubric["description"] += " " + text
        if current_rubric:
            rubrics.append(current_rubric)

    # Group the rubrics into page boundaries based on subject markers like "MIND p. 1"
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
        print(f"Fetching HTML from URL: {url}")
        try:
            html_content = fetch_html(url)
        except Exception as e:
            print(f"Error fetching the page: {e}")
            sys.exit(1)
    else:
        local_path = os.path.join("data", "raw", "kent0000_P1.html")
        print(f"No URL provided. Using local file: {local_path}")
        html_content = load_local_html(local_path)

    page_info = {"pages_covered": "p. 1-5"}
    chapter_entity = parse_chapter(html_content, page_info)
    save_chapter(chapter_entity)


if __name__ == "__main__":
    main()

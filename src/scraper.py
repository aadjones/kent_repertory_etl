import logging
import os
import sys

from bs4 import BeautifulSoup

from scraper_utils import (
    clean_header,
    extract_related_rubrics,
    fetch_html,
    group_by_page,
    is_decorative,
    load_and_normalize_html,
    parse_directory,
    parse_remedy_list,
    save_chapter,
)

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


def parse_chapter(html, page_info=None):
    soup = BeautifulSoup(html, "lxml")
    chapter = {}
    title_tag = soup.find("title")
    chapter_title = title_tag.get_text(strip=True) if title_tag else "No title found"
    chapter["title"] = chapter_title
    logging.info(f"Chapter title: {chapter_title}")
    if page_info:
        chapter["page_info"] = page_info

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
                header_text = BeautifulSoup(header_raw, "lxml").get_text(strip=True)
                header_clean = clean_header(header_text)
                description = BeautifulSoup(remedy_raw, "lxml").get_text(" ", strip=True)
                remedies = parse_remedy_list(remedy_raw)
                related = extract_related_rubrics(header_raw)
                current_rubric = {
                    "title": header_clean,
                    "related_rubrics": related,
                    "remedies": remedies,
                    "description": description,
                    "subrubrics": [],
                }
            else:
                header_text = BeautifulSoup(raw, "lxml").get_text(strip=True)
                current_rubric = {
                    "title": clean_header(header_text),
                    "related_rubrics": extract_related_rubrics(raw),
                    "remedies": [],
                    "description": "",
                    "subrubrics": [],
                }
            if current_rubric:
                rubrics.append(current_rubric)
        logging.debug(f"Parsed {len(rubrics)} rubrics using <p> tags.")

    pages = group_by_page(rubrics, subject_keyword="MIND")
    chapter["pages"] = pages
    chapter["subject"] = "MIND"
    chapter["section"] = "MIND"
    return chapter


def main():
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
        html_content = load_and_normalize_html(local_path)
    page_info = {"pages_covered": "p. 1-5"}
    chapter_entity = parse_chapter(html_content, page_info)
    save_chapter(chapter_entity)


if __name__ == "__main__":
    main()

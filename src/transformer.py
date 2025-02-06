from bs4 import BeautifulSoup

from remedy_parser import parse_remedy_list
from rubric_parser import extract_related_rubrics, group_by_page, parse_directory
from text_utils import clean_header, is_decorative


def transform_html_to_chapter(html, page_info=None):
    soup = BeautifulSoup(html, "lxml")
    chapter = {}

    # Extract title
    title_tag = soup.find("title")
    chapter_title = title_tag.get_text(strip=True) if title_tag else "No title found"
    chapter["title"] = chapter_title
    if page_info:
        chapter["page_info"] = page_info

    # Extract rubrics
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
    pages = group_by_page(rubrics, subject_keyword="MIND")
    chapter["pages"] = pages
    chapter["subject"] = "MIND"
    chapter["section"] = "MIND"
    return chapter

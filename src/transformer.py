# transformer.py
import logging

from bs4 import BeautifulSoup

from processing_utils import prune_empty_keys
from rubric_parser import parse_directory, transform_content
from text_utils import extract_section

logger = logging.getLogger(__name__)


def transform_html_to_chapter(html, page_info=None):
    soup = BeautifulSoup(html, "lxml")
    chapter = {}

    # Extract title from the <title> tag.
    title_tag = soup.find("title")
    chapter_title = title_tag.get_text(strip=True) if title_tag else "No title found"
    chapter["title"] = chapter_title

    # Extract the subject/section programmatically.
    section = extract_section(soup)
    chapter["section"] = section if section else None

    if page_info:
        chapter["page_info"] = page_info

    # Instead of grouping by page, simply parse the rubric directory.
    dir_tag = soup.find("dir")
    if dir_tag:
        # Here, we set a default current_page; if you have a different rule for starting page,
        # you can adjust this. (Often pages start at "P1" for the given section.)
        rubrics = parse_directory(dir_tag, current_page="P1", section=section)
    else:
        rubrics = []

    # Transform the raw rubric structure into your final schema.
    chapter["rubrics"] = transform_content(rubrics)

    # Remove keys that have empty values.
    chapter = prune_empty_keys(chapter)
    return chapter

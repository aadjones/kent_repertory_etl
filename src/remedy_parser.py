import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def parse_remedy(remedy_snippet):
    wrapped = f"<div>{remedy_snippet}</div>"
    frag = BeautifulSoup(wrapped, "lxml")
    grade = 1
    for font in frag.find_all("font"):
        color = font.get("color", "").lower()
        if color == "#ff0000":
            grade = 3
            break
        elif color == "#0000ff":
            grade = max(grade, 2)
    if grade == 1:
        if frag.find("b"):
            grade = 3
        elif frag.find("i"):
            grade = 2
    name = frag.get_text(strip=True)
    logger.debug(f"Parsed remedy: {name}, grade: {grade}")
    return {"name": name, "grade": grade}


def parse_remedy_list(remedy_html):
    remedy_parts = remedy_html.split(",")
    remedies = [parse_remedy(part) for part in remedy_parts if part.strip()]
    return remedies

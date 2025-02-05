import json
import logging
import os
import re

import requests
from bs4 import BeautifulSoup, Tag

# Configure logging for this module.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def fetch_html(url):
    """
    Fetch the HTML content from the given URL.
    Raises an HTTPError if the request fails.
    """
    logger.info(f"Fetching HTML from URL: {url}")
    response = requests.get(url)
    response.raise_for_status()
    logger.debug("HTML fetched successfully.")
    return response.text


def load_local_html(filepath):
    """
    Load the local HTML file from the given filepath.
    """
    logger.info(f"Loading local HTML file: {filepath}")
    with open(filepath, "r", encoding="windows-1252") as file:
        content = file.read()
    logger.debug("Local HTML loaded successfully.")
    return content


def is_decorative(text):
    """
    Return True if the text is considered decorative.
    This includes text that is solely hyphens, whitespace, arrow markers,
    or a combination of hyphens and '>' characters.
    """
    stripped = text.strip()
    if not stripped:
        return True
    if all(char in "- " for char in stripped):
        return True
    if ">>>" in stripped:
        return True
    if re.match(r"^[->]+$", stripped):
        return True
    return False


def remove_parentheses(text):
    """
    Remove any content inside parentheses (and the parentheses themselves).
    """
    return re.sub(r"\([^)]*\)", "", text)


def normalize_subject_title(title):
    """
    Normalize a subject title by removing any page markers like "p. 1".
    For example, "MIND p. 1" becomes "MIND".
    """
    normalized = re.sub(r"\s*p\.?\s*\d+", "", title, flags=re.IGNORECASE)
    return normalized.strip()


def merge_duplicate_rubrics(rubrics):
    """
    Merge rubrics with the same title.
    Merging is done by concatenating descriptions (with a space),
    extending remedy lists, and merging subrubrics.
    For remedy lists (which are lists of dictionaries), deduplicate using each remedy's (name, grade).
    """
    merged = {}
    order = []
    for rub in rubrics:
        title = rub.get("title", "").strip()
        key = title.lower()
        if key in merged:
            merged[key]["description"] += " " + rub.get("description", "")
            merged[key]["remedies"].extend(rub.get("remedies", []))
            merged[key]["subrubrics"].extend(rub.get("subrubrics", []))
        else:
            merged[key] = rub.copy()
            order.append(key)
    for key in merged:
        merged[key]["description"] = merged[key]["description"].strip()
        unique_remedies = []
        seen = set()
        for remedy in merged[key]["remedies"]:
            remedy_key = (remedy.get("name"), remedy.get("grade"))
            if remedy_key not in seen:
                seen.add(remedy_key)
                unique_remedies.append(remedy)
        merged[key]["remedies"] = unique_remedies
    logger.debug(f"Merged rubrics: {merged}")
    return [merged[k] for k in order]


def group_by_page(rubrics, subject_keyword="MIND"):
    """
    Group a flat list of rubric dictionaries into page boundaries.

    A rubric whose title matches a boundary pattern (e.g., "MIND p. 1") starts a new page.
    Such boundary markers are used only as markers and are not stored as content.
    Rubrics with a normalized title equal to the subject (e.g. "MIND") are skipped.
    """
    groups = []
    current_group = None
    page_pattern = re.compile(rf"^{subject_keyword}\s*p\.?\s*(\d+)", re.IGNORECASE)

    for rub in rubrics:
        title = rub.get("title", "")
        match = page_pattern.match(title)
        if match:
            page_num = match.group(1)
            logger.debug(f"Found page boundary: {rub['title']}")
            if current_group is None or current_group["page"] != f"P{page_num}":
                current_group = {"page": f"P{page_num}", "rubrics": []}
                groups.append(current_group)
            # Do not add the boundary rubric itself.
        else:
            if normalize_subject_title(title).upper() == subject_keyword.upper():
                logger.debug(f"Skipping redundant subject marker: {title}")
                continue
            if current_group is None:
                continue
            current_group["rubrics"].append(rub)
    for group in groups:
        group["rubrics"] = merge_duplicate_rubrics(group["rubrics"])
    logger.info(f"Grouped into pages: {[g['page'] for g in groups]}")
    return groups


def parse_remedy(remedy_snippet):
    """
    Parse a remedy snippet and return a dictionary with:
      - name: remedy name (plaintext)
      - grade: formatting grade (1 = plaintext, 2 = italic (blue), 3 = bold (red)).

    Wrap the snippet in a <div> so that BeautifulSoup can reliably parse the formatting.
    """
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
    """
    Given a remedy section as HTML (text after the colon), split by commas and parse each remedy.
    Returns a list of remedy dictionaries.
    """
    remedy_parts = remedy_html.split(",")
    remedies = [parse_remedy(part) for part in remedy_parts if part.strip()]
    return remedies


def parse_directory(tag, level=0):
    """
    Recursively parse a <dir> tag to extract rubrics in a hierarchical structure.

    Each rubric is represented as a dictionary with:
      - title, description, remedies (list of remedy dicts), subrubrics.

    Decorative paragraphs (e.g., "----------" or ">>>>") are skipped.
    For non-bold <p> tags, text is appended to the current rubric's description.
    """
    rubrics = []
    current_rubric = None
    for child in tag.children:
        if isinstance(child, Tag):
            if child.name == "p":
                raw = child.decode_contents()
                if is_decorative(raw):
                    logger.debug("Skipping decorative content.")
                    continue
                if child.find("b"):
                    if current_rubric:
                        rubrics.append(current_rubric)
                    if ":" in raw:
                        header_raw, remedy_raw = raw.split(":", 1)
                        header = BeautifulSoup(header_raw, "lxml").get_text(strip=True)
                        description = BeautifulSoup(remedy_raw, "lxml").get_text(" ", strip=True)
                        remedies = parse_remedy_list(remedy_raw)
                        current_rubric = {
                            "title": header,
                            "description": description,
                            "remedies": remedies,
                            "subrubrics": [],
                        }
                    else:
                        header = BeautifulSoup(raw, "lxml").get_text(strip=True)
                        current_rubric = {"title": header, "description": "", "remedies": [], "subrubrics": []}
                    logger.debug(f"New rubric: {current_rubric['title']}")
                else:
                    additional = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
                    if current_rubric:
                        current_rubric["description"] += " " + additional
                    else:
                        current_rubric = {"title": additional, "description": "", "remedies": [], "subrubrics": []}
            elif child.name == "dir":
                subrubrics = parse_directory(child, level + 1)
                if current_rubric:
                    current_rubric["subrubrics"].extend(subrubrics)
                else:
                    rubrics.extend(subrubrics)
            else:
                continue
    if current_rubric:
        rubrics.append(current_rubric)
    return rubrics


def clean_filename(text):
    """
    Clean up text to be safe for a filename:
      - Lowercase, replace spaces with underscores, remove non-alphanumeric characters.
    """
    text = text.lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    return text


def save_chapter(chapter, output_dir="data/processed"):
    """
    Save the chapter entity as a JSON file in the specified output directory.
    Filename is generated from the chapter title.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    filename = f"chapter_{clean_filename(chapter.get('title', 'chapter'))}.json"
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w", encoding="utf-8") as outfile:
        json.dump(chapter, outfile, indent=2, ensure_ascii=False)
    logger.info(f"Chapter saved to {output_path}")

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

    We assume that a rubric whose title matches a boundary pattern
    (e.g., "MIND p. 1", "MIND p. 2", etc.) marks the start of a new page.
    Such boundary rubrics are used only as markers and are not added to the page's rubric list.
    Also, if a rubric’s normalized title equals the subject keyword (e.g., "MIND")
    with no page marker, we skip it.

    If no boundary is found at all, then return a single page group (P1) that contains all rubrics.

    Returns a list of dictionaries, each with keys:
      - page: the page marker (e.g., "P1")
      - rubrics: list of rubric dictionaries belonging to that page.
    """
    import re

    groups = []
    current_group = None
    page_pattern = re.compile(rf"^{subject_keyword}\s*p\.?\s*(\d+)", re.IGNORECASE)

    for rub in rubrics:
        title = rub.get("title", "")
        match = page_pattern.match(title)
        if match:
            page_num = match.group(1)
            # Start a new group for a boundary marker.
            if current_group is None or current_group["page"] != f"P{page_num}":
                current_group = {"page": f"P{page_num}", "rubrics": []}
                groups.append(current_group)
            # Do not add the boundary rubric itself.
        else:
            if normalize_subject_title(title).upper() == subject_keyword.upper():
                continue
            if current_group is None:
                # If no boundary has been encountered yet, start a default group "P1".
                current_group = {"page": "P1", "rubrics": []}
                groups.append(current_group)
            current_group["rubrics"].append(rub)
    for group in groups:
        group["rubrics"] = merge_duplicate_rubrics(group["rubrics"])
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
    Recursively parse a <dir> tag to extract rubrics and subrubrics.

    For each <p> tag, if a colon is present in its raw HTML content, split on the first colon.
    The left-hand side is used as the rubric title and the right-hand side is interpreted
    as the remedy section. Any colon characters are then removed.

    If no colon is present, then treat the paragraph as additional detail to be appended
    to the description of the current rubric.

    Returns a list of rubric dictionaries, each with keys:
      - title: (colon-free)
      - description: additional details (colon-free)
      - remedies: list of remedy dictionaries (parsed from the remedy section, if any)
      - subrubrics: list of nested rubric dictionaries (if any)
    """
    rubrics = []
    current_rubric = None
    for child in tag.children:
        if not isinstance(child, Tag):
            continue
        if child.name == "p":
            raw = child.decode_contents()
            if is_decorative(raw):
                continue
            # If a colon is present anywhere in the raw HTML, split on the first colon.
            if ":" in raw:
                header_raw, remedy_raw = raw.split(":", 1)
                header = BeautifulSoup(header_raw, "lxml").get_text(strip=True)
                header = header.replace(":", "").strip()
                # Parse remedy part:
                description = BeautifulSoup(remedy_raw, "lxml").get_text(" ", strip=True)
                description = description.replace(":", "").strip()
                remedies = parse_remedy_list(remedy_raw)
                # Create a new rubric from the split result.
                rubric = {"title": header, "description": description, "remedies": remedies, "subrubrics": []}
                current_rubric = rubric
                rubrics.append(rubric)
            else:
                # No colon: treat this as additional information.
                text = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
                text = text.replace(":", "").strip()
                if current_rubric:
                    # Append to the description.
                    current_rubric["description"] += " " + text
                else:
                    # If no rubric exists, create one with this text as the title.
                    current_rubric = {"title": text, "description": "", "remedies": [], "subrubrics": []}
                    rubrics.append(current_rubric)
        elif child.name == "dir":
            # Recursively process nested <dir> tags.
            subrubrics = parse_directory(child, level + 1)
            if current_rubric:
                current_rubric["subrubrics"].extend(subrubrics)
            else:
                rubrics.extend(subrubrics)
        else:
            continue
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

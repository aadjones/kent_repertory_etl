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
    Decorative text is usually just hyphens or arrow markers.
    However, if the text contains a page boundary marker (e.g. "p. 1")
    or a section marker (e.g. "MIND p. 1"), then it is NOT decorative.
    """
    stripped = text.strip()
    # If the text matches a page-boundary pattern, then it's not decorative.
    import re

    if re.search(r"\bp\.?\s*\d+", stripped, re.IGNORECASE):
        return False
    # Otherwise, consider it decorative if it's empty or made only of hyphens and spaces.
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
    Merging is done by extending remedy lists and merging subrubrics.
    For remedy lists (lists of dictionaries), deduplicate using each remedy's (name, grade).
    This version ignores descriptions completely.
    """
    merged = {}
    order = []
    for rub in rubrics:
        title = rub.get("title", "").strip()
        key = title.lower()
        if key in merged:
            # Extend remedy lists and subrubrics.
            merged[key]["remedies"].extend(rub.get("remedies", []))
            merged[key]["subrubrics"].extend(rub.get("subrubrics", []))
        else:
            # Copy the rubric; if it has a description, ignore it in the final merged output.
            new_rub = rub.copy()
            new_rub.pop("description", None)
            merged[key] = new_rub
            order.append(key)
    # Deduplicate remedies using (name, grade)
    for key in merged:
        unique_remedies = []
        seen = set()
        for remedy in merged[key]["remedies"]:
            remedy_key = (remedy.get("name"), remedy.get("grade"))
            if remedy_key not in seen:
                seen.add(remedy_key)
                unique_remedies.append(remedy)
        merged[key]["remedies"] = unique_remedies
    return [merged[k] for k in order]


def group_by_page(rubrics, subject_keyword=None):
    """
    Group a list of rubric dictionaries into pages based on boundary markers.

    A boundary marker is any rubric whose title contains a page marker, e.g.
    "MIND p. 100" or "VERTIGO p. 96". If subject_keyword is provided, the boundary
    must start with that keyword; otherwise, we match any boundary marker.

    We assume that each HTML file is expected to cover exactly 5 pages.

    The function iterates over the rubrics in order. When a rubric's title matches
    the boundary pattern, a new page group is started (using the number captured).
    Otherwise, rubrics are added to the current page.

    Returns a list of page groups. Each page group is a dictionary:
      { "page": "P<number>", "rubrics": [ list of rubric dictionaries ] }
    """
    import re

    pages = []
    current_page = None

    if subject_keyword:
        # Pattern with one capturing group: the page number.
        boundary_pattern = re.compile(rf"^{subject_keyword}\s*p\.?\s*(\d+)", re.IGNORECASE)
    else:
        # Pattern with two capturing groups: group(1) is section, group(2) is page number.
        boundary_pattern = re.compile(r"^(.*?)\s*p\.?\s*(\d+)", re.IGNORECASE)

    for rub in rubrics:
        title = rub.get("title", "").strip()
        m = boundary_pattern.match(title)
        if m:
            # If subject_keyword is provided, the page number is in group(1); otherwise in group(2).
            if subject_keyword:
                page_num = m.group(1).strip()
            else:
                page_num = m.group(2).strip()
            # Start a new page group.
            current_page = {"page": f"P{page_num}", "rubrics": []}
            pages.append(current_page)
        else:
            if current_page is None:
                # If no boundary has been encountered yet, start a default group "P1".
                current_page = {"page": "P1", "rubrics": []}
                pages.append(current_page)
            current_page["rubrics"].append(rub)
    return pages


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


def extract_section_from_raw(html):
    """
    Scan the raw HTML (after extracting visible text) for a section boundary pattern.
    Look for a string such as "MIND p. 1" or "VERTIGO p. 96" and return the text before
    the page marker (uppercased), ignoring any match that equals "KENT".
    """
    import re

    from bs4 import BeautifulSoup

    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    pattern = re.compile(r"([A-Z]+(?:\s+[A-Z]+)*)\s*p\.?\s*\d+", re.IGNORECASE)
    matches = pattern.findall(text)
    # Debug: print("DEBUG: Matches found:", matches)
    for m in matches:
        section = m.strip().upper()
        if section != "KENT" and len(section) >= 3:
            return section
    return None


def extract_section(rubrics):
    """
    Scan the list of parsed rubrics for a section boundary.
    Look for the first rubric whose title matches the pattern
         <Section Name> p. <number>
    and return the section portion (uppercased). If none is found, return "UNKNOWN".
    """
    pattern = re.compile(r"^(?!KENT\b)(.*?)\s*p\.?\s*\d+", re.IGNORECASE)
    for rub in rubrics:
        title = rub.get("title", "").strip()
        m = pattern.match(title)
        if m:
            section = m.group(1).strip()
            if section:
                return section.upper()
    return "UNKNOWN"

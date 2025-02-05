import json
import os
import re

import requests
from bs4 import BeautifulSoup, Tag


def fetch_html(url):
    """
    Fetch the HTML content from the given URL.
    Raises an HTTPError if the request fails.
    """
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def load_local_html(filepath):
    """
    Load the local HTML file from the given filepath.
    """
    with open(filepath, "r", encoding="windows-1252") as file:
        return file.read()


def is_decorative(text):
    """
    Return True if the text is considered decorative.
    This includes text that consists solely of hyphens and whitespace,
    text that contains arrow markers (e.g., ">>>>"), or that matches
    a pattern of only hyphens and '>' characters.
    """
    stripped = text.strip()
    if not stripped:
        return True
    if all(char in "- " for char in stripped):
        return True
    if ">>>" in stripped:
        return True
    # Additional check: if the text is entirely made up of hyphens and arrows.
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
    Given a list of rubric dictionaries, merge those with the same title.
    Two rubrics are considered duplicates if their title (after lowercasing
    and stripping) is identical.

    Merging is done by concatenating descriptions (with a space),
    extending remedy lists, and merging subrubrics.

    For remedy lists (lists of dictionaries), deduplicate them using
    each remedy's (name, grade) as a key.
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
    return [merged[k] for k in order]


def group_by_page(rubrics, subject_keyword="MIND"):
    """
    Group a flat list of rubric dictionaries into page boundaries.

    We assume that a rubric whose title matches a boundary pattern
    (e.g., "MIND p. 1", "MIND p. 2", etc.) marks the start of a new page.
    That boundary rubric is used solely as a marker and is not added
    to the page's rubric list. Also, if a rubric’s normalized title equals
    the subject keyword (e.g., "MIND") with no page marker, we skip it.

    Returns a list of dictionaries, each with keys:
      - page: the page marker (e.g., "P1")
      - rubrics: list of rubric dictionaries belonging to that page.
    """
    groups = []
    current_group = None
    page_pattern = re.compile(rf"^{subject_keyword}\s*p\.?\s*(\d+)", re.IGNORECASE)

    for rub in rubrics:
        title = rub.get("title", "")
        match = page_pattern.match(title)
        if match:
            page_num = match.group(1)
            if current_group is None or current_group["page"] != f"P{page_num}":
                current_group = {"page": f"P{page_num}", "rubrics": []}
                groups.append(current_group)
            # Boundary rubric is used only as a marker; do not add.
        else:
            if normalize_subject_title(title).upper() == subject_keyword.upper():
                continue
            if current_group is None:
                continue
            current_group["rubrics"].append(rub)
    for group in groups:
        group["rubrics"] = merge_duplicate_rubrics(group["rubrics"])
    return groups


def parse_remedy(remedy_snippet):
    """
    Given a remedy snippet (a string of HTML or plain text), return a dictionary
    with keys:
      - name: remedy name (plaintext)
      - grade: an integer indicating formatting:
               plaintext = 1, italic (blue) = 2, bold (red) = 3.

    We wrap the snippet in a <div> so BeautifulSoup can parse it properly.
    Bold remedies are identified by a <font> tag with color "#ff0000",
    italic remedies by a <font> tag with color "#0000ff". Bold takes precedence.
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
    return {"name": name, "grade": grade}


def parse_remedy_list(remedy_html):
    """
    Given a remedy section as HTML (the part after the colon),
    split it by commas and parse each remedy snippet.
    Returns a list of remedy dictionaries.
    """
    remedy_parts = remedy_html.split(",")
    remedies = [parse_remedy(part) for part in remedy_parts if part.strip()]
    return remedies


def parse_directory(tag, level=0):
    """
    Recursively parse a <dir> tag to extract rubrics in a hierarchical structure.

    Each rubric is represented as a dictionary with:
      - title: text of the rubric (with parentheses removed)
      - description: text following a colon if present
      - remedies: list of remedy dictionaries (if present)
      - subrubrics: list of child rubrics (parsed recursively)

    Decorative paragraphs (e.g., "----------" or ">>>>") are skipped.
    For <p> tags that do not contain a <b> tag, if there is an existing current rubric,
    the text is appended to its description.
    """
    rubrics = []
    current_rubric = None
    for child in tag.children:
        if isinstance(child, Tag):
            if child.name == "p":
                raw = child.decode_contents()
                if is_decorative(raw):
                    continue
                # Check if this <p> contains a bold tag; if so, it's a new rubric header.
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
                else:
                    # If this <p> is not bold, then append its text to the current rubric's description
                    # (if a current rubric exists); otherwise, treat it as a new rubric.
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
      - Lowercase the text,
      - Replace spaces with underscores,
      - Remove non-alphanumeric characters.
    """
    text = text.lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    return text


def save_chapter(chapter, output_dir="data/processed"):
    """
    Save the chapter entity as a JSON file in the specified output directory.
    The filename is generated from the chapter title.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    filename = f"chapter_{clean_filename(chapter.get('title', 'chapter'))}.json"
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w", encoding="utf-8") as outfile:
        json.dump(chapter, outfile, indent=2, ensure_ascii=False)
    print(f"Chapter saved to {output_path}")

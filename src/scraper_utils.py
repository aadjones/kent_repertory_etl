import json
import os
import re

import requests
from bs4 import Tag


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
    Return True if the text consists only of hyphens (and whitespace)
    or looks like a decorative separator (e.g., contains ">>>>").
    """
    stripped = text.strip()
    if not stripped:
        return True
    if all(char in "- " for char in stripped):
        return True
    if ">>>" in stripped:
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
        merged[key]["remedies"] = list(dict.fromkeys(merged[key]["remedies"]))
    return [merged[k] for k in order]


def group_by_page(rubrics, subject_keyword="MIND"):
    """
    Group a flat list of rubric dictionaries into page boundaries.

    We assume that a rubric whose title matches a boundary pattern
    (e.g., "MIND p. 1", "MIND p. 2", etc.) marks the start of a new page.
    That boundary rubric is used solely as a marker and is not added
    to the page's rubric list. Also, if a rubric’s normalized title equals
    the subject keyword (e.g. "MIND") with no page marker, we skip it.

    Returns a list of dictionaries, each with keys:
      - page: the page marker (e.g., "P1")
      - rubrics: list of rubric dictionaries belonging to that page.
    """
    groups = []
    current_group = None
    # Regex to detect boundaries such as "MIND p. 1" (captures the number).
    page_pattern = re.compile(rf"^{subject_keyword}\s*p\.?\s*(\d+)", re.IGNORECASE)

    for rub in rubrics:
        title = rub.get("title", "")
        match = page_pattern.match(title)
        if match:
            # This rubric is a boundary marker.
            page_num = match.group(1)
            if current_group is None or current_group["page"] != f"P{page_num}":
                current_group = {"page": f"P{page_num}", "rubrics": []}
                groups.append(current_group)
            # Do not add the boundary rubric itself.
        else:
            # If normalized title equals subject keyword ("MIND"), skip it.
            if normalize_subject_title(title).upper() == subject_keyword.upper():
                continue
            if current_group is None:
                continue
            current_group["rubrics"].append(rub)
    for group in groups:
        group["rubrics"] = merge_duplicate_rubrics(group["rubrics"])
    return groups


def parse_directory(tag, level=0):
    """
    Recursively parse a <dir> tag to extract rubrics in a hierarchical structure.

    Each rubric is represented as a dictionary with:
      - title: text of the rubric (with parentheses removed)
      - description: text following a colon if present
      - remedies: list of remedy abbreviations (if present)
      - subrubrics: list of child rubrics (parsed recursively)

    Decorative paragraphs (e.g., "----------" or ">>>>") are skipped.
    """
    rubrics = []
    for child in tag.children:
        if isinstance(child, Tag):
            if child.name == "p":
                text = child.get_text(" ", strip=True)
                if is_decorative(text):
                    continue
                text = remove_parentheses(text)
                rubric = {"title": "", "description": "", "remedies": [], "subrubrics": []}
                if ":" in text:
                    header, remedy_text = text.split(":", 1)
                    rubric["title"] = header.strip()
                    rubric["description"] = remedy_text.strip()
                    remedies = [r.strip() for r in remedy_text.split(",") if r.strip()]
                    rubric["remedies"] = remedies
                else:
                    rubric["title"] = text.strip()
                rubrics.append(rubric)
            elif child.name == "dir":
                subrubrics = parse_directory(child, level + 1)
                if rubrics:
                    rubrics[-1]["subrubrics"].extend(subrubrics)
                else:
                    rubrics.extend(subrubrics)
            else:
                continue
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

import json
import os
import re
import sys

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
    the subject keyword (e.g. "MIND"), we skip it.

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
            # This rubric is a boundary marker.
            page_num = match.group(1)
            if current_group is None or current_group["page"] != f"P{page_num}":
                current_group = {"page": f"P{page_num}", "rubrics": []}
                groups.append(current_group)
            # Do not add the boundary rubric itself.
        else:
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

    # Extract chapter title.
    title_tag = soup.find("title")
    chapter_title = title_tag.get_text(strip=True) if title_tag else "No title found"
    chapter["title"] = chapter_title

    # We no longer include anchors.

    # Parse rubrics: first try using nested <dir> tags; if not, fallback to <p> tags.
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

    # Group the rubrics into page boundaries using the subject marker "MIND".
    pages = group_by_page(rubrics, subject_keyword="MIND")
    chapter["pages"] = pages
    chapter["subject"] = "MIND"
    return chapter


def clean_filename(text):
    """
    Clean up text to be safe for a filename:
      - Lowercase,
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
        except requests.HTTPError as e:
            print(f"Error fetching the page: {e}")
            sys.exit(1)
    else:
        local_path = os.path.join("data", "raw", "kent0000_P1.html")
        print(f"No URL provided. Using local file: {local_path}")
        html_content = load_local_html(local_path)

    # Indicate that this file covers pages 1-5.
    page_info = {"pages_covered": "p. 1-5"}
    chapter_entity = parse_chapter(html_content, page_info)
    save_chapter(chapter_entity)


if __name__ == "__main__":
    main()

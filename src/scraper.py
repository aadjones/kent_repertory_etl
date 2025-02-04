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
    response.raise_for_status()  # Raise an error for bad responses.
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
    or if it is a decorative arrow line (e.g., containing ">>>>").
    """
    stripped = text.strip()
    if not stripped:
        return True
    # If the text is only hyphens or arrows, return True.
    if all(char in "->" for char in stripped):
        return True
    return False


def remove_parentheses(text):
    """
    Remove any content inside parentheses (and the parentheses themselves).
    """
    return re.sub(r"\([^)]*\)", "", text)


def normalize_subject_title(title):
    """
    Normalize a subject title by removing any page markers such as "p. 1".
    For example, "MIND p. 1" becomes "MIND".
    """
    # Remove any "p. <number>" (case-insensitive) from the title.
    normalized = re.sub(r"\s*p\.\s*\d+", "", title, flags=re.IGNORECASE)
    return normalized.strip()


def merge_duplicate_subjects(rubrics):
    """
    Given a list of rubric dictionaries (each with keys: "title", "description",
    "remedies", and "subrubrics"), merge rubrics that represent the same subject.

    We ignore any rubric whose normalized title is "KENT".
    If duplicate subjects are found (e.g., "MIND p. 1" and "MIND"), we merge
    their descriptions, remedy lists, and subrubrics.
    """
    merged = {}
    order = []  # To preserve original order.

    for rub in rubrics:
        title = rub.get("title", "")
        norm = normalize_subject_title(title)
        # Skip if the normalized title is "kent" (we ignore the top-level "KENT" marker)
        if norm.lower() == "kent":
            continue
        # Also ignore titles that look decorative (for example, those containing ">>>>")
        if ">>>" in title:
            continue

        if norm in merged:
            # Merge the descriptions (concatenate) and extend remedies and subrubrics.
            merged[norm]["description"] += " " + rub.get("description", "")
            merged[norm]["remedies"].extend(rub.get("remedies", []))
            merged[norm]["subrubrics"].extend(rub.get("subrubrics", []))
        else:
            merged[norm] = rub.copy()
            # Overwrite title with the normalized version if desired.
            merged[norm]["title"] = norm
            order.append(norm)

    # Return the merged rubrics in the order they first appeared.
    return [merged[key] for key in order]


def parse_directory(tag, level=0):
    """
    Recursively parse a <dir> tag to extract rubrics in a hierarchical structure.

    Each rubric is represented as a dictionary with:
      - title: text of the rubric (with parentheses removed)
      - remedies: a list of remedy abbreviations (if text after a colon is present)
      - subrubrics: a list of child rubrics (parsed recursively)

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
                    rubric["description"] = ""
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
    Parse the HTML of a single page into a Chapter entity.

    The structure we assume:
      - The page begins with a top-level decorative section (e.g. "KENT" and decorative lines) that we ignore.
      - Then comes a subject heading (for example, "MIND p. 1") that defines the parent subject for that page.
      - Under the subject, there are rubric entries (and subrubrics) that form the tree structure.

    Returns a dictionary representing the chapter, with keys:
      - title
      - anchors (list)
      - rubrics (list, hierarchical structure)
      - (optionally) page_info
    """
    soup = BeautifulSoup(html, "lxml")
    chapter = {}

    # Chapter title from the <title> tag.
    title_tag = soup.find("title")
    chapter_title = title_tag.get_text(strip=True) if title_tag else "No title found"
    chapter["title"] = chapter_title

    # Optional page_info (e.g., page number) can be stored.
    if page_info:
        chapter["page_info"] = page_info

    # Extract anchors.
    chapter["anchors"] = []
    for a in soup.find_all("a", attrs={"name": True}):
        chapter["anchors"].append({"name": a.get("name"), "text": a.get_text(strip=True)})

    # Look for the outer <dir> element.
    dir_tag = soup.find("dir")
    if dir_tag:
        rubrics = parse_directory(dir_tag)
    else:
        # Fallback: flat parsing from <p> tags.
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

    # Merge duplicate subject headings.
    chapter["rubrics"] = merge_duplicate_subjects(rubrics)
    return chapter


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

    # Optionally, if you want to pass page info (e.g., from filename "kent0000_P1.html")
    page_info = {"page": "P1"}

    chapter_entity = parse_chapter(html_content, page_info)
    save_chapter(chapter_entity)


if __name__ == "__main__":
    main()

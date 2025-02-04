import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

from utils import is_decorative


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


def parse_chapter(html):
    """
    Parse the HTML of a single page into a 'Chapter' entity.

    The Chapter entity is a dictionary with:
      - title: The chapter title from the <title> tag.
      - anchors: A list of anchors (each with 'name' and 'text') from <a> tags with a NAME attribute.
      - rubrics: A list of rubric entities parsed from <p> tags.

    A new rubric is started when a <p> tag contains a <b> tag.
    Decorative paragraphs (e.g., "----------") are skipped.
    Non-bold paragraphs (if not decorative) are appended to the current rubric's description.
    If a rubric header contains a colon ":", it is split into a header part and a remedy list part.
    """
    soup = BeautifulSoup(html, "lxml")
    chapter = {}

    # Extract chapter title from the <title> tag.
    title_tag = soup.find("title")
    chapter["title"] = title_tag.get_text(strip=True) if title_tag else "No title found"

    # Extract all anchors with a NAME attribute.
    chapter["anchors"] = []
    for a in soup.find_all("a", attrs={"name": True}):
        chapter["anchors"].append({"name": a.get("name"), "text": a.get_text(strip=True)})

    rubrics = []
    current_rubric = None
    paragraphs = soup.find_all("p")

    for p in paragraphs:
        # Get the text with a space between inline elements.
        text = p.get_text(" ", strip=True)
        if is_decorative(text):
            continue

        # If the paragraph contains a <b> tag, treat it as a rubric header.
        if p.find("b"):
            # Save the previous rubric (if any).
            if current_rubric:
                rubrics.append(current_rubric)
            # Split the text on a colon if present to separate header and remedy list.
            if ":" in text:
                rubric_header, remedy_text = text.split(":", 1)
            else:
                rubric_header = text
                remedy_text = ""
            current_rubric = {"title": rubric_header.strip(), "description": remedy_text.strip(), "remedies": []}
            # If remedy_text exists, split remedies by commas.
            if remedy_text:
                remedies = [r.strip() for r in remedy_text.split(",") if r.strip()]
                current_rubric["remedies"] = remedies
        else:
            # Append non-bold paragraph text to the current rubric's description.
            if current_rubric:
                current_rubric["description"] += " " + text

    # Append the last rubric if it exists.
    if current_rubric:
        rubrics.append(current_rubric)

    chapter["rubrics"] = rubrics
    return chapter


def clean_filename(text):
    """
    Clean up text to be safe for a filename.
    Lowercase the text, replace spaces with underscores, and remove non-alphanumeric characters.
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

    # Generate a safe filename based on the chapter title.
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

    # Parse the HTML into a chapter entity.
    chapter_entity = parse_chapter(html_content)
    # Save the chapter entity to a JSON file.
    save_chapter(chapter_entity)


if __name__ == "__main__":
    main()

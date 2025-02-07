import re

from bs4 import BeautifulSoup


# Detects whether a given text is decorative, i.e. it doesn't contain any
# information that would be relevant for a reader.
def is_decorative(text):
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


# Removes text within parentheses.
def remove_parentheses(text):
    return re.sub(r"\([^)]*\)", "", text)


# Removes page numbers from a subject title.
def normalize_subject_title(title):
    normalized = re.sub(r"\s*p\.?\s*\d+", "", title, flags=re.IGNORECASE)
    return normalized.strip()


# Removes text within parentheses from a header.
def clean_header(header):
    cleaned = re.sub(r"\s*\([^)]*\)", "", header)
    return cleaned.strip()


def clean_filename(text):
    text = text.lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    return text


def is_page_break(text, subject_keyword=None):
    """
    Determine whether a given text represents a page break.

    Returns True if:
      - The text consists only of dashes, arrows, and/or whitespace.
      - OR if a subject keyword is provided and the text matches the pattern
        "<subject_keyword> p. <number>" (ignoring case).
      - OR if no subject keyword is provided, it detects a generic pattern:
        an uppercase word (of length 3 or more) followed by "p." and a number.
    """
    # First, strip any HTML tags so we're working only with the visible text.
    text = BeautifulSoup(text, "lxml").get_text(" ", strip=True)
    text = text.strip()

    # Check if the text is only dashes, arrows, and whitespace.
    if re.fullmatch(r"[->\s]+", text):
        return True

    # If a subject keyword is provided, use that in our regex.
    if subject_keyword:
        pattern = rf"{subject_keyword}\s*p\.?\s*\d+"
        if re.search(pattern, text, re.IGNORECASE):
            return True
    else:
        # Otherwise, use a generic pattern.
        if re.search(r"\b[A-Z]{3,}\s*p\.?\s*\d+\b", text):
            return True

    return False


def extract_page_number(text, subject_keyword=None):
    """
    Extracts the page number from a text string that contains a pattern like
    "MIND p. 5" or "[subject_keyword] p. <number>".

    - If a subject_keyword is provided, it searches for that keyword followed by "p." and a number.
    - If not provided, it uses a generic pattern that looks for any uppercase word (at least 3 letters)
      followed by "p." and a number.

    Returns a string like "P5" if found, otherwise None.
    """
    text = text.strip()
    if subject_keyword:
        pattern = rf"{subject_keyword}\s*p\.?\s*(\d+)"
        match = re.search(pattern, text, re.IGNORECASE)
    else:
        # Generic pattern: uppercase word (at least 3 letters) followed by p. and a number.
        match = re.search(r"\b[A-Z]{3,}\s*p\.?\s*(\d+)\b", text)
    if match:
        return f"P{match.group(1)}"
    return None


def extract_section(soup):
    """
    Scan all <p> tags in the document to find one that matches a pattern like
    "MIND p. 1". Returns the extracted section (e.g., "MIND") or None if not found.
    """
    # Get all paragraph elements
    paragraphs = soup.find_all("p")
    # Look for a paragraph whose text matches our section pattern.
    for p in paragraphs:
        text = p.get_text(" ", strip=True)
        # The pattern looks for a word (typically in uppercase) followed by "p." and a number.
        match = re.match(r"^([A-Z]+)\s*p\.?\s*\d+", text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def compute_page_range(kent_identifier):
    """
    Given a Kent file identifier (as a string, e.g. "0000" or "0005"),
    compute and return a string for the page range, e.g., "p. 1-5" or "p. 6-10".
    """
    base = int(kent_identifier)
    start_page = base + 1
    end_page = base + 5
    return f"p. {start_page}-{end_page}"

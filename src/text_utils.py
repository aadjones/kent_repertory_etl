import re


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


def remove_parentheses(text):
    return re.sub(r"\([^)]*\)", "", text)


def normalize_subject_title(title):
    normalized = re.sub(r"\s*p\.?\s*\d+", "", title, flags=re.IGNORECASE)
    return normalized.strip()


def clean_header(header):
    cleaned = re.sub(r"\s*\([^)]*\)", "", header)
    return cleaned.strip()


def clean_filename(text):
    text = text.lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    return text


def is_page_break(text):
    """
    Check if the provided text represents a page break.
    We consider it a page break if it starts with many dashes or if it contains a pattern like "MIND p. <number>".
    """
    text = text.strip()
    if text.startswith("----------"):
        return True
    if re.search(r"MIND\s*p\.?\s*\d+", text, re.IGNORECASE):
        return True
    return False


def extract_page_number(text):
    """
    Extracts the page number from a text string that contains a pattern like "MIND p. 5".
    Returns a string like "P5" if found, otherwise None.
    """
    match = re.search(r"MIND\s*p\.?\s*(\d+)", text, re.IGNORECASE)
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

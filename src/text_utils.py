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

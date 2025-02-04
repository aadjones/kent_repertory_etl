def clean_text(text):
    """
    For now, simply trim extraneous whitespace.
    More rules can be added later based on actual data.
    """
    return " ".join(text.strip().split())


def is_decorative(text):
    """
    Return True if the text consists only of hyphens (and possibly whitespace).
    """
    stripped = text.strip()
    # If after stripping whitespace the text is all hyphens, return True.
    return stripped and all(char == "-" for char in stripped)

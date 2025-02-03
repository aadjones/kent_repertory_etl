def clean_text(text):
    """
    For now, simply trim extraneous whitespace.
    More rules can be added later based on actual data.
    """
    return " ".join(text.strip().split())

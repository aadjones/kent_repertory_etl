from src.utils import clean_text


def test_trims_whitespace():
    raw_text = "  MINDp. 1  "
    expected = "MINDp. 1"
    cleaned = clean_text(raw_text)
    assert cleaned == expected, f"Expected '{expected}', got '{cleaned}'"

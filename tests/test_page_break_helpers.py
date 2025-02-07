from rubric_parser import extract_page_number, is_page_break


def test_is_page_break():
    # A typical page break marker
    text = "---------- MIND p. 5"
    assert is_page_break(text) is True

    # A string that isn’t a page break
    text2 = "ANXIETY: remedy1, remedy2"
    assert is_page_break(text2) is False


def test_extract_page_number():
    text = "---------- MIND p. 5"
    page = extract_page_number(text)
    assert page == "P5"

    text_no_page = "----------"
    page_none = extract_page_number(text_no_page)
    assert page_none is None

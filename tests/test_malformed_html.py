from bs4 import BeautifulSoup

from src.rubric_parser import parse_directory


def test_problematic_header_extraction():
    # This snippet mimics a header that might be problematic.
    # For example, no <b> tag is present or it is malformed, but it contains the parenthesized content.
    html = """
    <dir>
       <p>ABANDONED (See Forsaken)</p>
    </dir>
    """
    soup = BeautifulSoup(html, "lxml")
    rubrics = parse_directory(soup.find("dir"))
    # We expect one rubric
    assert len(rubrics) == 1, f"Expected 1 rubric, got {len(rubrics)}"

    rubric = rubrics[0]
    # The title should be cleaned of the parenthesized content.
    assert rubric["title"] == "ABANDONED", f"Expected title 'ABANDONED', got '{rubric['title']}'"
    # The related rubrics should be extracted.
    assert rubric["related_rubrics"] == [
        "Forsaken"
    ], f"Expected related rubrics ['Forsaken'], got {rubric['related_rubrics']}"
    # Since there's no colon, the remedy list and description should be empty.
    assert rubric["remedies"] == [], f"Expected empty remedies list, got {rubric['remedies']}"
    assert rubric["description"] == "", f"Expected empty description, got '{rubric['description']}'"

from bs4 import BeautifulSoup

from rubric_parser import parse_directory


def test_parse_directory_page_break():
    html = """
    <dir>
      <p><b>MIND p. 1</b></p>
      <p><b>ANXIETY: remedy1</b></p>
      <p>---------- MIND p. 5</p>
      <p><b>DEPRESSIVE: remedy2</b></p>
    </dir>
    """
    soup = BeautifulSoup(html, "lxml")
    dir_tag = soup.find("dir")
    # Start with a default current_page of "P1"
    rubrics = parse_directory(dir_tag, current_page="P1")

    # We expect two rubrics:
    #   - The first rubric ("ANXIETY") should have page "P1"
    #   - The second rubric ("DEPRESSIVE") should have page "P5"
    assert len(rubrics) == 2, f"Expected 2 rubrics, got {len(rubrics)}"
    assert rubrics[0]["title"].upper().startswith("ANXIETY"), f"First rubric title: {rubrics[0]['title']}"
    assert rubrics[0]["page"] == "P1", f"Expected first rubric page to be 'P1', got {rubrics[0]['page']}"
    assert rubrics[1]["title"].upper().startswith("DEPRESSIVE"), f"Second rubric title: {rubrics[1]['title']}"
    assert rubrics[1]["page"] == "P5", f"Expected second rubric page to be 'P5', got {rubrics[1]['page']}"

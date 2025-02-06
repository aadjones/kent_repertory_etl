from bs4 import BeautifulSoup

from src.rubric_parser import extract_related_rubrics, parse_directory
from src.text_utils import clean_header, is_decorative

# ----------------------------
# Test for related rubrics extraction
# ----------------------------


def test_extract_related_rubrics_single():
    header = "ABANDONED (See Forsaken)"
    related = extract_related_rubrics(header)
    assert related == ["Forsaken"], f"Expected ['Forsaken'], got {related}"


def test_extract_related_rubrics_multiple():
    header = "AFFECTIONATE (See Love, Indifference)"
    related = extract_related_rubrics(header)
    assert related == ["Love", "Indifference"], f"Expected ['Love', 'Indifference'], got {related}"


def test_clean_header():
    header = "ABANDONED (See Forsaken)"
    cleaned = clean_header(header)
    assert cleaned == "ABANDONED", f"Expected 'ABANDONED', got '{cleaned}'"


# ----------------------------
# Test for decorative filtering
# ----------------------------


def test_is_decorative():
    assert is_decorative("----------") is True
    assert is_decorative("   ---   ") is True
    assert is_decorative("---------->>>>>") is True
    assert is_decorative("----  >>>>") is True
    # A non-decorative string should return False.
    assert is_decorative("MIND p. 1") is False


# ----------------------------
# Test for parse_directory excluding decorative rubrics
# ----------------------------

# ----------------------------
# Test for Excluding Decorative Rubrics
# ----------------------------


def test_parse_directory_excludes_decorative():
    html = """
    <dir>
      <p>---------->>>>> </p>
      <p><b>ABSENT-MINDED (See Forsaken): Acon., calc.</b></p>
      <p>Additional info for ABSENT-MINDED</p>
    </dir>
    """
    soup = BeautifulSoup(html, "lxml")
    rubrics = parse_directory(soup.find("dir"))
    # The decorative paragraph should be skipped.
    # We expect one rubric from the non-decorative header.
    assert len(rubrics) == 1, f"Expected 1 rubric, got {len(rubrics)}"
    rubric = rubrics[0]
    # The rubric title should be cleaned of the parenthesized content.
    assert rubric["title"] == "ABSENT-MINDED", f"Expected title 'ABSENT-MINDED', got '{rubric['title']}'"
    # Our new design extracts related rubrics from the header,
    # so we expect the related rubrics list to contain ["Forsaken"]
    assert rubric.get("related_rubrics") == [
        "Forsaken"
    ], f"Expected related rubrics ['Forsaken'], got {rubric.get('related_rubrics')}"


# ----------------------------
# Test for decorative rubric not being included at all (via grouping)
# ----------------------------


def test_decorative_rubric_not_included():
    # This snippet simulates a page boundary followed by a decorative rubric.
    html = """
    <dir>
      <p><b>MIND p. 1</b></p>
      <p><b>ABSENT-MINDED (See Forsaken): Acon., calc.</b></p>
      <p><b>---------->>>>> </b></p>
    </dir>
    """
    soup = BeautifulSoup(html, "lxml")
    rubrics = parse_directory(soup.find("dir"))
    # When later grouping by page, the decorative rubric should be filtered out.
    # Here, ensure that none of the rubrics have a title that is purely decorative.
    for rub in rubrics:
        assert not is_decorative(rub["title"]), f"Found decorative rubric title: '{rub['title']}'"


def test_related_rubrics_extraction_only():
    html = """
    <dir>
      <p><b>ABANDONED (See Forsaken)</b></p>
    </dir>
    """
    soup = BeautifulSoup(html, "lxml")
    rubrics = parse_directory(soup.find("dir"))
    # We expect one rubric with title "ABANDONED", related rubrics ["Forsaken"],
    # and an empty remedy list and empty description.
    assert len(rubrics) == 1, f"Expected 1 rubric, got {len(rubrics)}"
    rubric = rubrics[0]
    assert rubric["title"] == "ABANDONED", f"Expected title 'ABANDONED', got '{rubric['title']}'"
    assert rubric["related_rubrics"] == [
        "Forsaken"
    ], f"Expected related rubrics ['Forsaken'], got {rubric['related_rubrics']}"
    assert rubric["remedies"] == [], "Expected empty remedies list"
    assert rubric["description"] == "", "Expected empty description"


def test_related_rubrics_extraction_with_remedies():
    html = """
    <dir>
      <p><b>AFFECTIONATE (See Love, Indifference): Acon., calc.</b></p>
    </dir>
    """
    soup = BeautifulSoup(html, "lxml")
    rubrics = parse_directory(soup.find("dir"))
    # Expect one rubric with title "AFFECTIONATE", related rubrics ["Love", "Indifference"],
    # and the remedies list parsed from "Acon., calc."
    assert len(rubrics) == 1, f"Expected 1 rubric, got {len(rubrics)}"
    rubric = rubrics[0]
    assert rubric["title"] == "AFFECTIONATE", f"Expected title 'AFFECTIONATE', got '{rubric['title']}'"
    assert rubric["related_rubrics"] == [
        "Love",
        "Indifference",
    ], f"Expected related rubrics ['Love', 'Indifference'], got {rubric['related_rubrics']}"
    # Remedies should be parsed normally (test remedy parser separately).
    remedy_names = [r["name"] for r in rubric["remedies"]]
    assert "Acon." in remedy_names
    assert "calc." in remedy_names

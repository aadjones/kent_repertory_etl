from bs4 import BeautifulSoup

from scraper import parse_chapter
from scraper_utils import (
    is_decorative,
    merge_duplicate_rubrics,
    normalize_subject_title,
    parse_directory,
    parse_remedy,
    parse_remedy_list,
)

# ----------------------------
# Test for decorator nonsense
# ----------------------------


def test_is_decorative_all_hyphens():
    assert is_decorative("----------")
    assert is_decorative("   ---   ")


def test_is_decorative_arrows():
    assert is_decorative(">>>>")
    assert is_decorative("---->>>>>----")


def test_is_decorative_empty():
    assert is_decorative("")
    assert is_decorative("   ")


# ----------------------------
# Test for subject extraction
# ----------------------------


def test_normalize_subject_title():
    # "MIND p. 1" should normalize to "MIND"
    normalized = normalize_subject_title("MIND p. 1")
    assert normalized == "MIND"
    # Other examples
    normalized = normalize_subject_title("MIND P. 23")
    assert normalized == "MIND"
    normalized = normalize_subject_title("MIND")
    assert normalized == "MIND"


# ----------------------------
# Test for rubric extraction
# ----------------------------


def test_parse_directory_simple_rubric():
    # A simple HTML snippet containing a rubric in a <p> tag.
    html = "<dir><p><b>ABSENT-MINDED: Acon., calc.</b></p></dir>"
    soup = BeautifulSoup(html, "lxml")
    rubrics = parse_directory(soup.find("dir"))
    # We expect one rubric with title "ABSENT-MINDED" and remedies Acon. and calc.
    assert len(rubrics) == 1
    rub = rubrics[0]
    assert rub["title"] == "ABSENT-MINDED"
    assert "Acon." in [r["name"] for r in rub["remedies"]]
    # Grade checking will be done in remedy tests


# ----------------------------
# Test for subrubric extraction
# ----------------------------


def test_parse_directory_nested():
    # Create a nested directory structure
    html = """
    <dir>
      <p><b>ABSENT-MINDED: Acon., calc.</b></p>
      <dir>
         <p><b>morning: <i><font COLOR="#0000ff">tarent.</font></i></b></p>
         <p>Extra detail for morning</p>
      </dir>
    </dir>
    """
    soup = BeautifulSoup(html, "lxml")
    rubrics = parse_directory(soup.find("dir"))
    # Expect one top-level rubric with one subrubric.
    assert len(rubrics) == 1
    parent = rubrics[0]
    assert parent["title"] == "ABSENT-MINDED"
    assert len(parent["subrubrics"]) == 1
    child = parent["subrubrics"][0]
    # Check that the child rubric's title is "morning" (the <i><font> formatting should be removed in title)
    assert child["title"].lower() == "morning"
    # The remedy "tarent." should be present in the child's remedy list.
    remedy_names = [r["name"].lower() for r in child["remedies"]]
    assert "tarent." in remedy_names


# ----------------------------
# Test for remedy extraction (individual snippet)
# ----------------------------


def test_parse_remedy_plain():
    # Plain remedy should yield grade 1.
    snippet = "calc."
    remedy = parse_remedy(snippet)
    assert remedy["name"].lower() == "calc."
    assert remedy["grade"] == 1


def test_parse_remedy_bold():
    # Bold remedy: <b><font COLOR="#ff0000">Acon.</b></font>
    snippet = '<b><font COLOR="#ff0000">Acon.</b></font>'
    remedy = parse_remedy(snippet)
    assert remedy["name"].lower() == "acon."
    assert remedy["grade"] == 3


def test_parse_remedy_italic():
    # Italic remedy: <i><font COLOR="#0000ff">tarent.</font></i>
    snippet = '<i><font COLOR="#0000ff">tarent.</font></i>'
    remedy = parse_remedy(snippet)
    assert remedy["name"].lower() == "tarent."
    assert remedy["grade"] == 2


# ----------------------------
# Test for remedy list extraction
# ----------------------------


def test_parse_remedy_list():
    # Test a remedy section with multiple remedies with mixed formatting.
    remedy_html = ' <b><font COLOR="#ff0000">Acon.</b></font>, alum., <i><font COLOR="#0000ff">tarent.</font></i> '
    remedies = parse_remedy_list(remedy_html)
    # We expect three remedies: Acon. (bold, grade 3), alum. (plain, grade 1), tarent. (italic, grade 2)
    assert len(remedies) == 3
    # Build a mapping for easier checking.
    mapping = {r["name"].lower(): r["grade"] for r in remedies}
    assert mapping.get("acon.") == 3
    assert mapping.get("alum.") == 1
    assert mapping.get("tarent.") == 2


# ----------------------------
# Test for merging duplicate rubrics
# ----------------------------


def test_merge_duplicate_rubrics():
    # Provide two rubrics with the same title.
    rubrics = [
        {"title": "AMOROUS", "description": "desc1", "remedies": [{"name": "calc.", "grade": 1}], "subrubrics": []},
        {"title": "AMOROUS", "description": "desc2", "remedies": [{"name": "calc.", "grade": 1}], "subrubrics": []},
    ]
    merged = merge_duplicate_rubrics(rubrics)
    assert len(merged) == 1
    merged_rub = merged[0]
    assert "desc1" in merged_rub["description"]
    assert "desc2" in merged_rub["description"]
    # Remedies should be merged (and deduplicated) so that there is only one entry.
    assert len(merged_rub["remedies"]) == 1


# ----------------------------
# Test for subject extraction in full chapter parsing
# ----------------------------


def test_parse_chapter_subject():
    # Test an HTML snippet representing a chapter with subject boundaries.
    # For simplicity, we simulate two page boundaries.
    html = """
    <html>
      <head><title>KENT0000</title></head>
      <body>
         <dir>
           <p><b>MIND p. 1</b></p>
           <p><b>ABSENT-MINDED: <i><font COLOR="#0000ff">tarent.</font></i>, alum.</b></p>
           <p><b>MIND p. 2</b></p>
           <p><b>AMOROUS: <b><font COLOR="#ff0000">Acon.</b></font>, calc.</b></p>
           <p>---------->>>>></p>
         </dir>
      </body>
    </html>
    """
    chapter = parse_chapter(html, page_info={"pages_covered": "p. 1-5"})
    # Expect chapter title "KENT0000", subject "MIND", and two page groups: P1 and P2.
    assert chapter["title"] == "KENT0000"
    assert chapter["subject"] == "MIND"
    pages = chapter["pages"]
    assert len(pages) == 2
    # For P1, we expect one rubric ("ABSENT-MINDED")
    page1 = pages[0]
    assert page1["page"] == "P1"
    # Ensure that the boundary rubric "MIND p. 1" is not included in the rubrics.
    for rub in page1["rubrics"]:
        assert normalize_subject_title(rub["title"]).upper() != "MIND"
    # For P2, we expect one rubric ("AMOROUS")
    page2 = pages[1]
    assert page2["page"] == "P2"
    for rub in page2["rubrics"]:
        assert normalize_subject_title(rub["title"]).upper() != "MIND"

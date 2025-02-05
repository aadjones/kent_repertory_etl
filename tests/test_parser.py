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

# --- Decorative content tests ---


def test_is_decorative_all_hyphens():
    assert is_decorative("----------")
    assert is_decorative("   ---   ")


def test_is_decorative_arrows():
    assert is_decorative(">>>>")
    assert is_decorative("---->>>>>----")


def test_is_decorative_mixed():
    # Test a string that is only hyphens and arrow characters.
    assert is_decorative("---------->>>>>")


def test_is_decorative_empty():
    assert is_decorative("")
    assert is_decorative("   ")


# --- Subject extraction tests ---


def test_normalize_subject_title():
    assert normalize_subject_title("MIND p. 1") == "MIND"
    assert normalize_subject_title("MIND P. 23") == "MIND"
    assert normalize_subject_title("MIND") == "MIND"


# --- Rubric extraction tests ---


def test_parse_directory_simple_rubric():
    # A simple HTML snippet containing a rubric.
    html = "<dir><p><b>ABSENT-MINDED: Acon., calc.</b></p></dir>"
    soup = BeautifulSoup(html, "lxml")
    rubrics = parse_directory(soup.find("dir"))
    # Expect one rubric with title "ABSENT-MINDED" and remedies for Acon. and calc.
    assert len(rubrics) == 1
    rub = rubrics[0]
    assert rub["title"] == "ABSENT-MINDED"
    remedy_names = [r["name"] for r in rub["remedies"]]
    assert "Acon." in remedy_names
    assert "calc." in remedy_names


# --- Subrubric extraction tests ---


def test_parse_directory_nested():
    # Create a nested directory structure.
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
    # There should be exactly one subrubric under the parent.
    assert len(parent["subrubrics"]) == 1
    child = parent["subrubrics"][0]
    # The child rubric's title should be "morning" (after stripping formatting).
    assert child["title"].lower() == "morning"
    # The remedy "tarent." should be present with the correct grade.
    remedy_names = [r["name"].lower() for r in child["remedies"]]
    assert "tarent." in remedy_names


# --- Remedy extraction tests ---


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


def test_parse_remedy_list():
    # Remedy list with mixed formatting.
    remedy_html = ' <b><font COLOR="#ff0000">Acon.</b></font>, alum., <i><font COLOR="#0000ff">tarent.</font></i> '
    remedies = parse_remedy_list(remedy_html)
    assert len(remedies) == 3
    mapping = {r["name"].lower(): r["grade"] for r in remedies}
    assert mapping.get("acon.") == 3
    assert mapping.get("alum.") == 1
    assert mapping.get("tarent.") == 2


# --- Merging duplicate rubrics tests ---


def test_merge_duplicate_rubrics():
    rubrics = [
        {"title": "AMOROUS", "description": "desc1", "remedies": [{"name": "calc.", "grade": 1}], "subrubrics": []},
        {"title": "AMOROUS", "description": "desc2", "remedies": [{"name": "calc.", "grade": 1}], "subrubrics": []},
    ]
    merged = merge_duplicate_rubrics(rubrics)
    assert len(merged) == 1
    merged_rub = merged[0]
    assert "desc1" in merged_rub["description"]
    assert "desc2" in merged_rub["description"]
    assert len(merged_rub["remedies"]) == 1


# --- Final schema verification tests ---


def test_parse_chapter_schema():
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
    # Check that chapter has expected top-level keys.
    for key in ["title", "subject", "pages"]:
        assert key in chapter, f"Missing key '{key}' in chapter."
    # Check that each page group has "page" and "rubrics".
    for page in chapter["pages"]:
        for key in ["page", "rubrics"]:
            assert key in page, f"Missing key '{key}' in page group."

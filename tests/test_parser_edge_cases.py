from bs4 import BeautifulSoup

from scraper import parse_chapter
from scraper_utils import (
    clean_header,
    extract_related_rubrics,
    is_decorative,
    merge_duplicate_rubrics,
    normalize_subject_title,
    parse_directory,
    parse_remedy,
    parse_remedy_list,
)

# ----------------------------
# Decorative Content Tests
# ----------------------------


def test_is_decorative_all_hyphens():
    assert is_decorative("----------")
    assert is_decorative("   ---   ")


def test_is_decorative_arrows():
    assert is_decorative(">>>>")
    assert is_decorative("---->>>>>----")


def test_is_decorative_mixed():
    assert is_decorative("---------->>>>>")
    assert is_decorative("----  >>>>")


def test_is_decorative_empty():
    assert is_decorative("")
    assert is_decorative("   ")


# ----------------------------
# Subject / Section Extraction Tests
# ----------------------------


def test_normalize_subject_title():
    # "MIND p. 1" should normalize to "MIND"
    assert normalize_subject_title("MIND p. 1") == "MIND"
    assert normalize_subject_title("MIND P. 23") == "MIND"
    assert normalize_subject_title("MIND") == "MIND"


# ----------------------------
# Related Rubrics and Header Cleaning Tests
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
# Rubric Extraction Tests
# ----------------------------


def test_parse_directory_simple_rubric():
    # A simple HTML snippet containing one rubric in a <p> tag.
    html = "<dir><p><b>ABSENT-MINDED: Acon., calc.</b></p></dir>"
    soup = BeautifulSoup(html, "lxml")
    rubrics = parse_directory(soup.find("dir"))
    # Expect one rubric with title "ABSENT-MINDED" (cleaned) and remedies for Acon. and calc.
    assert len(rubrics) == 1, f"Expected 1 rubric, got {len(rubrics)}"
    rub = rubrics[0]
    assert rub["title"] == "ABSENT-MINDED", f"Expected title 'ABSENT-MINDED', got '{rub['title']}'"
    remedy_names = [r["name"] for r in rub["remedies"]]
    assert "Acon." in remedy_names
    assert "calc." in remedy_names


# ----------------------------
# Subrubric Extraction Tests
# ----------------------------


def test_parse_directory_nested():
    # Create a nested structure: one top-level rubric and one nested subrubric.
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
    # We expect one top-level rubric ("ABSENT-MINDED") with one subrubric ("morning").
    assert len(rubrics) == 1, f"Expected 1 top-level rubric, got {len(rubrics)}"
    parent = rubrics[0]
    assert parent["title"] == "ABSENT-MINDED", f"Expected parent title 'ABSENT-MINDED', got '{parent['title']}'"
    assert len(parent["subrubrics"]) == 1, f"Expected 1 subrubric, got {len(parent['subrubrics'])}"
    child = parent["subrubrics"][0]
    assert child["title"].lower() == "morning", f"Expected subrubric title 'morning', got '{child['title']}'"
    remedy_names = [r["name"].lower() for r in child["remedies"]]
    assert "tarent." in remedy_names, f"Expected remedy 'tarent.' in subrubric remedies, got {child['remedies']}"


# ----------------------------
# Remedy Extraction Tests
# ----------------------------


def test_parse_remedy_plain():
    snippet = "calc."
    remedy = parse_remedy(snippet)
    assert remedy["name"].lower() == "calc."
    assert remedy["grade"] == 1


def test_parse_remedy_bold():
    snippet = '<b><font COLOR="#ff0000">Acon.</b></font>'
    remedy = parse_remedy(snippet)
    assert remedy["name"].lower() == "acon."
    assert remedy["grade"] == 3


def test_parse_remedy_italic():
    snippet = '<i><font COLOR="#0000ff">tarent.</font></i>'
    remedy = parse_remedy(snippet)
    assert remedy["name"].lower() == "tarent."
    assert remedy["grade"] == 2


def test_parse_remedy_list():
    remedy_html = ' <b><font COLOR="#ff0000">Acon.</b></font>, alum., <i><font COLOR="#0000ff">tarent.</font></i> '
    remedies = parse_remedy_list(remedy_html)
    assert len(remedies) == 3, f"Expected 3 remedies, got {len(remedies)}"
    mapping = {r["name"].lower(): r["grade"] for r in remedies}
    assert mapping.get("acon.") == 3
    assert mapping.get("alum.") == 1
    assert mapping.get("tarent.") == 2


# ----------------------------
# Duplicate Rubric Merging Tests
# ----------------------------


def test_merge_duplicate_rubrics():
    rubrics = [
        {"title": "AMOROUS", "description": "desc1", "remedies": [{"name": "calc.", "grade": 1}], "subrubrics": []},
        {"title": "AMOROUS", "description": "desc2", "remedies": [{"name": "calc.", "grade": 1}], "subrubrics": []},
    ]
    # Ensure every rubric has a 'description' key (default to empty string if not present).
    for rub in rubrics:
        rub.setdefault("description", "")
    merged = merge_duplicate_rubrics(rubrics)
    assert len(merged) == 1, f"Expected merged list length 1, got {len(merged)}"
    merged_rub = merged[0]
    assert "desc1" in merged_rub["description"]
    assert "desc2" in merged_rub["description"]
    assert len(merged_rub["remedies"]) == 1


# ----------------------------
# Test for Excluding Decorative Rubrics
# ----------------------------


def test_decorative_rubric_not_included():
    html = """
    <dir>
      <p><b>MIND p. 1</b></p>
      <p><b>ABSENT-MINDED (See Forsaken): Acon., calc.</b></p>
      <p><b>---------->>>>> </b></p>
    </dir>
    """
    soup = BeautifulSoup(html, "lxml")
    rubrics = parse_directory(soup.find("dir"))
    # None of the rubrics should have a title that is purely decorative.
    for rub in rubrics:
        assert not is_decorative(rub["title"]), f"Found decorative rubric title: '{rub['title']}'"


# ----------------------------
# Test for Full Chapter Parsing and Schema
# ----------------------------


def test_parse_chapter_schema():
    html = """
    <html>
      <head><title>KENT0000</title></head>
      <body>
         <dir>
           <p><b>MIND p. 1</b></p>
           <p><b>ABSENT-MINDED (See Forsaken): <i><font COLOR="#0000ff">tarent.</font></i>, alum.</b></p>
           <dir>
              <p>morning : Guai., nat-c., ph-ac., phos.</p>
              <p>11 a.m. to 4 p.m. : Kali-n.</p>
           </dir>
           <p><b>MIND p. 2</b></p>
           <p><b>AMOROUS (See Lewdness): <b><font COLOR="#ff0000">Acon.</b></font>, calc.</b></p>
           <p>---------->>>>></p>
         </dir>
      </body>
    </html>
    """
    chapter = parse_chapter(html, page_info={"pages_covered": "p. 1-5"})
    # Verify top-level keys exist.
    for key in ["title", "subject", "pages"]:
        assert key in chapter, f"Missing key '{key}' in chapter."
    # For this project, we want a 'section' key as well; we'll set it equal to the subject.
    chapter["section"] = chapter["subject"]
    assert chapter["section"] == "MIND"
    # Check that pages were created.
    assert len(chapter["pages"]) >= 1, "No pages were created."
    # Ensure that boundary rubrics like "MIND p. 1" do not appear as actual rubric content.
    for page in chapter["pages"]:
        for rub in page["content"]:
            assert (
                normalize_subject_title(rub["title"]).upper() != "MIND"
            ), f"Found redundant subject marker '{rub['title']}' in page {page['page']}"

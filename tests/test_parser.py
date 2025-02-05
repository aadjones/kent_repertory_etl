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


def test_subrubric_extraction():

    html = (
        "<dir>"
        '  <p><b><a NAME="ABSENTMINDED">ABSENT</a>-MINDED : <i><font COLOR="#0000ff">Acon.</font>, </i>'
        'act-sp., aesc., agar., <i><font COLOR="#0000ff">agn.</font>, </i>all-c., '
        '<i><font COLOR="#0000ff">alum.</font>, <font COLOR="#0000ff">am-c.</font>, </i>'
        'am-m., <i><font COLOR="#0000ff">anac.</font>, </i>ang., <b><font COLOR="#ff0000">Apis.'
        '</b></font>, arg-m., <i><font COLOR="#0000ff">arn.</font>, </i>ars., arum-t., asar., '
        '<i><font COLOR="#0000ff">aur.</font>, <font COLOR="#0000ff">bar-c.</font>, '
        '<font COLOR="#0000ff">bell.</font>, <font COLOR="#0000ff">bov.</font>, '
        '<font COLOR="#0000ff">bufo.</font>, <font COLOR="#0000ff">calad.</font>, </i>'
        'calc-s., calc., <b><font COLOR="#ff0000">Cann-i.</b></font>, cann-s., caps., '
        'carb-ac., carb-s., <i><font COLOR="#0000ff">carl.</font>, </i>'
        '<b><font COLOR="#ff0000">Caust.</b></font>, cench., <b><font COLOR="#ff0000">Cham.'
        '</b></font>, chel., chin., <i><font COLOR="#0000ff">cic.</font>, </i>clem., '
        '<i><font COLOR="#0000ff">cocc.</font>, </i>coff., colch., coloc., con., croc., '
        'crot-h., <i><font COLOR="#0000ff">cupr.</font>, </i>cycl., daph., dirc., dulc., '
        'elaps., <i><font COLOR="#0000ff">graph.</font>, </i>guai., ham., '
        '<b><font COLOR="#ff0000">Hell.</b></font>, hep., hura., <i><font COLOR="#0000ff">'
        'hyos.</font>, <font COLOR="#0000ff">ign.</font>, </i>jug-c., <i><font COLOR="#0000ff">'
        'kali-br.</font>, <font COLOR="#0000ff">kali-c.</font>, <font COLOR="#0000ff">'
        'kali-p.</font>, </i>kali-s., <i><font COLOR="#0000ff">kreos.</font>, '
        '<font COLOR="#0000ff">lac-c.</font>, </i><b><font COLOR="#ff0000">Lach.'
        '</b></font>, led., <i><font COLOR="#0000ff">lyc.</font>, </i>lyss., '
        '<i><font COLOR="#0000ff">mag-c.</font>, </i>manc., mang., <i><font COLOR="#0000ff">'
        'merc.</font>, </i><b><font COLOR="#ff0000">Mez.</b></font>, <i><font COLOR="#0000ff">'
        'mosch.</font>, </i>naja., nat-c., <b><font COLOR="#ff0000">Nat-m.</b></font>, '
        'nat-p., nit-ac., <b><font COLOR="#ff0000">Nux-m.</b></font>, <i><font COLOR="#0000ff">'
        'nux-v.</font>, <font COLOR="#0000ff">olnd.</font>, <font COLOR="#0000ff">onos.</font>, '
        '<font COLOR="#0000ff">op.</font>, <font COLOR="#0000ff">petr.</font>, '
        '<font COLOR="#0000ff">ph-ac.</font>, <font COLOR="#0000ff">phos.</font>, </i>'
        '<b><font COLOR="#ff0000">Plat.</b></font>, <i><font COLOR="#0000ff">plb.</font>, </i>'
        '<b><font COLOR="#ff0000">Puls.</b></font>, rhod., <i><font COLOR="#0000ff">rhus-t.</font>, '
        '</i>rhus-v., ruta., sars., <b><font COLOR="#ff0000">Sep.</b></font>, '
        '<i><font COLOR="#0000ff">sil.</font>, </i>spong., stann., stram., sul-ac., '
        '<i><font COLOR="#0000ff">sulph.</font>, </i>tarent., thuj., <b><font COLOR="#ff0000">'
        "Verat.</b></font>, verb., viol-o., viol-t., zinc.</p>"
        "<dir>"
        "  <p>morning : Guai., nat-c., ph-ac., phos.</p>"
        "  <p>11 a.m. to 4 p.m. : Kali-n.</p>"
        "  <p>noon : Mosch.</p>"
        "  <p>menses, during : Calc.</p>"
        "  <p>periodical attacks of, short lasting : Fl-ac., "
        '<i><font COLOR="#0000ff">nux-m.</font></i></p>'
        "  <p>reading, while : Agn., lach., "
        '<i><font COLOR="#0000ff">nux-m.</font></i>, ph-ac.</p>'
        "  <p>starts when spoken to : Carb-ac.</p>"
        "  <p>writing, while : Mag-c.</p>"
        "</dir>"
        "</dir>"
    )

    # Parse the snippet into a chapter
    chapter = parse_chapter(html)

    # There should be at least one page in the output.
    assert len(chapter["pages"]) >= 1, "No pages were created."

    # For the top-level rubric, we expect the title to be "ABSENTMINDED" (without colons).
    top_rubric = chapter["pages"][0]["rubrics"][0]
    normalized_title = top_rubric["title"].replace("-", "").replace(" ", "").upper()
    assert "ABSENTMINDED" in normalized_title, "Top-level rubric title not as expected."

    # Verify that no colons appear n any parsed text
    def check_no_colon(item):
        assert ":" not in item.get("title", ""), f"Colon found in title: {item.get('title')}"
        assert ":" not in item.get("description", ""), f"Colon found in description: {item.get('description')}"
        for remedy in item.get("remedies", []):
            assert ":" not in remedy.get("name", ""), f"Colon found in remedy name: {remedy.get('name')}"
        for sub in item.get("subrubrics", []):
            check_no_colon(sub)

    # Check all top-level rubrics and their subrubrics
    for page in chapter["pages"]:
        for rub in page["rubrics"]:
            check_no_colon(rub)

    # Check subrubric "morning" exists and its remedies are as expected.
    # Find a subrubric with "morning" in its title.
    morning_found = False
    for rub in top_rubric.get("subrubrics", []):
        if "morning" in rub["title"].lower():
            morning_found = True
            remedy_names = [r["name"].strip() for r in rub["remedies"]]
            expected_remedies = ["Guai.", "nat-c.", "ph-ac.", "phos."]
            for exp in expected_remedies:
                assert exp.lower() in [
                    r.lower() for r in remedy_names
                ], f"Expected remedy {exp} not found in 'morning'."
    assert morning_found, "Subrubric 'morning' not found."


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

def test_group_by_page_boundaries():
    # Create a list of rubric dictionaries with boundary markers and some content.
    rubrics = [
        {"title": "VERTIGO p. 100", "remedies": [], "subrubrics": []},
        {"title": "Rubric A", "remedies": [{"name": "RemedyA", "grade": 1}], "subrubrics": []},
        {"title": "Rubric B", "remedies": [{"name": "RemedyB", "grade": 2}], "subrubrics": []},
        {"title": "VERTIGO p. 101", "remedies": [], "subrubrics": []},
        {"title": "Rubric C", "remedies": [{"name": "RemedyC", "grade": 1}], "subrubrics": []},
        {"title": "Rubric D", "remedies": [{"name": "RemedyD", "grade": 2}], "subrubrics": []},
        {"title": "VERTIGO p. 102", "remedies": [], "subrubrics": []},
        {"title": "Rubric E", "remedies": [{"name": "RemedyE", "grade": 1}], "subrubrics": []},
        {"title": "Rubric F", "remedies": [{"name": "RemedyF", "grade": 2}], "subrubrics": []},
        {"title": "VERTIGO p. 103", "remedies": [], "subrubrics": []},
        {"title": "Rubric G", "remedies": [{"name": "RemedyG", "grade": 1}], "subrubrics": []},
    ]

    # Import the group_by_page function from your scraper_utils.
    from src.scraper_utils import group_by_page

    # We pass the subject keyword as "VERTIGO" so that boundaries like "VERTIGO p. 100" are recognized.
    pages = group_by_page(rubrics, subject_keyword="VERTIGO")

    # We expect the boundaries to produce four groups:
    # one for page 100 (starting with "VERTIGO p. 100"),
    # one for page 101, one for page 102, and one for page 103.
    expected_page_markers = ["P100", "P101", "P102", "P103"]
    assert len(pages) == len(
        expected_page_markers
    ), f"Expected {len(expected_page_markers)} page groups, got {len(pages)}"

    for page, expected in zip(pages, expected_page_markers):
        assert page["page"] == expected, f"Expected page marker {expected}, got {page['page']}"

    # Optionally, check that each page group contains the content that follows its boundary
    # For example, the first group should contain "Rubric A" and "Rubric B" (if present)
    # and the next boundary ("VERTIGO p. 101") should start a new group.
    # (You can add further assertions here as needed.)

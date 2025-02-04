from src.scraper import parse_chapter


def test_ignore_decorative_lines():
    # Sample HTML with a bold rubric header, a decorative line, and additional description.
    sample_html = """
    <html>
      <head><title>Test Chapter</title></head>
      <body>
        <p><b>MIND p. 1 : Acon., calc.</b></p>
        <p>----------</p>
        <p>Additional description text.</p>
      </body>
    </html>
    """
    chapter = parse_chapter(sample_html)
    rubrics = chapter["rubrics"]

    # We expect only one rubric, and the decorative line should be ignored.
    assert len(rubrics) == 1
    rubric = rubrics[0]
    # The title should be "MIND p. 1" (before the colon).
    assert rubric["title"] == "MIND p. 1"
    # The description should include both "Acon., calc." (from the header after colon)
    # and "Additional description text." appended from the next paragraph.
    assert "Additional description text." in rubric["description"]


def test_rubric_boundary_without_decorative():
    # Sample HTML where the first paragraph is a rubric header, followed by a normal paragraph.
    sample_html = """
    <html>
      <head><title>Test Chapter</title></head>
      <body>
        <p><b>HEARING p. 321 : Impaired, right</b></p>
        <p>This is a description of impaired hearing on the right.</p>
      </body>
    </html>
    """
    chapter = parse_chapter(sample_html)
    rubrics = chapter["rubrics"]

    assert len(rubrics) == 1
    rubric = rubrics[0]
    assert rubric["title"] == "HEARING p. 321"
    # Ensure the description includes the remedy list part ("Impaired, right") and the additional description.
    assert "Impaired, right" in rubric["description"]
    assert "This is a description of impaired hearing on the right." in rubric["description"]

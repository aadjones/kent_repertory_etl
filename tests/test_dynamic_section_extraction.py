def test_dynamic_section_extraction():
    html = """
    <html>
      <head><title>KENT0000</title></head>
      <body>
         <p>KENT</p>
         <p>----------</p>
         <p>MIND p. 1</p>
         <dir>
             <p><b>ABSENT-MINDED : <i><font COLOR="#0000ff">Acon.</font>, act-sp.</b></p>
         </dir>
      </body>
    </html>
    """
    from src.scraper import parse_chapter

    chapter = parse_chapter(html, page_info={"pages_covered": "p. 1-5"})
    # The section should be extracted as "MIND" from the line "MIND p. 1"
    assert chapter["section"] == "MIND", f"Expected section 'MIND', got {chapter['section']}"

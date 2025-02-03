import os
import pytest
from bs4 import BeautifulSoup

# Assume your scraper functions are in src/scraper.py.
# For this example, we’ll refactor the functions you already wrote
# into a module that we can import here.
from src.scraper import load_local_html

# We can define a fixture for loading our sample HTML file.
@pytest.fixture
def sample_html():
    filepath = os.path.join("data", "raw", "kent0000_P1.html")
    return load_local_html(filepath)

def test_title_extraction(sample_html):
    """Test that the title is correctly extracted."""
    soup = BeautifulSoup(sample_html, "lxml")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    assert title == "KENT0000", f"Expected title to be 'KENT0000', got '{title}'"

def test_anchor_extraction(sample_html):
    """Test that named anchors are found and correctly extracted."""
    soup = BeautifulSoup(sample_html, "lxml")
    anchors = soup.find_all("a", attrs={"name": True})
    names = [a.get("name") for a in anchors]
    
    expected_names = ["P1", "ABSENTMINDED", "ABSORBED", "P2", "ANGER", "P3", "P4", "ANXIETY", "P5"]
    for name in expected_names:
        assert name in names, f"Expected anchor name '{name}' not found."

def test_paragraph_extraction(sample_html):
    """Test that a few paragraphs are extracted and not empty."""
    soup = BeautifulSoup(sample_html, "lxml")
    paragraphs = soup.find_all("p")
    # Check that the first few paragraphs contain expected text snippets.
    assert paragraphs, "No paragraphs found in the sample HTML."

    first_paragraph = paragraphs[0].get_text(strip=True)
    assert "KENT" in first_paragraph, f"Expected 'KENT' in first paragraph, got '{first_paragraph}'"

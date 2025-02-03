import os
from bs4 import BeautifulSoup

def load_local_html(filepath):
    """Load the local HTML file."""
    with open(filepath, "r", encoding="windows-1252") as file:
        return file.read()

def parse_sample(html):
    """Parse the HTML and extract a small subset of data."""
    soup = BeautifulSoup(html, "lxml")
    
    # Example 1: Extract the title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "No title found"
    print("Title:", title)
    
    # Example 2: Extract all anchor tags with a NAME attribute (e.g., <a NAME="P1">)
    anchors_with_name = soup.find_all("a", attrs={"name": True})
    for a in anchors_with_name:
        name_attr = a.get("name")
        text = a.get_text(strip=True)
        print(f"Found anchor with NAME='{name_attr}': {text}")
    
    # Example 3: Extract paragraph tags (<p>) that might represent rubric descriptions
    paragraphs = soup.find_all("p")
    for i, p in enumerate(paragraphs[:5]):  # Limit to first 5 for brevity
        print(f"Paragraph {i+1}:", p.get_text(strip=True))

if __name__ == "__main__":
    # Define the path to the sample HTML file (adjust as needed)
    sample_filepath = os.path.join("data", "raw", "kent0000_P1.html")
    html_content = load_local_html(sample_filepath)
    parse_sample(html_content)

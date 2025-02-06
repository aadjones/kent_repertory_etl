from extractor_utils import fetch_html, load_and_normalize_html


def extract_source(url=None, local_path=None):
    if url:
        html_content = fetch_html(url)
    elif local_path:
        html_content = load_and_normalize_html(local_path)
    else:
        raise ValueError("A URL or local_path must be provided.")
    return html_content

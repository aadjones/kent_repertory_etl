import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def fetch_html(url):
    logger.info(f"Fetching HTML from URL: {url}")
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def load_local_html(filepath):
    logger.info(f"Loading local HTML file: {filepath}")
    with open(filepath, "r", encoding="windows-1252") as file:
        return file.read()


def load_and_normalize_html(filepath):
    """Load and normalize HTML using html5lib."""
    with open(filepath, "r", encoding="windows-1252") as file:
        raw_html = file.read()
    soup = BeautifulSoup(raw_html, "html5lib")
    return str(soup)

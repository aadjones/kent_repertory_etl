import json
import logging
import os

from text_utils import clean_filename

logger = logging.getLogger(__name__)


def save_chapter(chapter, output_dir="data/processed"):
    """
    Save the chapter dictionary as a JSON file.
    The filename is constructed from the chapter title (which includes the Kent identifier).
    For example, if chapter["title"] is "KENT0000", the output file will be
    "chapter_kent0000.json" inside output_dir.
    """
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Created directory {output_dir}")
        except Exception as e:
            logger.error(f"Could not create directory {output_dir}: {e}")
            raise

    # Use the chapter title (or a default value) to build the filename.
    chapter_title = chapter.get("title", "chapter")
    safe_title = clean_filename(chapter_title)
    filename = f"{safe_title}.json"
    filepath = os.path.join(output_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(chapter, file, indent=2)
        logger.info(f"Chapter saved successfully to {filepath}")
    except Exception as e:
        logger.error(f"Error saving chapter: {e}")
        raise

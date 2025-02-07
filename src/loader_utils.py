import json
import logging
import os

logger = logging.getLogger(__name__)


def save_chapter(chapter, filepath="data/processed/chapter.json"):
    # Ensure the directory exists
    output_dir = os.path.dirname(filepath)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Created directory {output_dir}")
        except Exception as e:
            logger.error(f"Could not create directory {output_dir}: {e}")
            raise

    try:
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(chapter, file, indent=2)
        logger.info(f"Chapter saved successfully to {filepath}")
    except Exception as e:
        logger.error(f"Error saving chapter: {e}")
        raise

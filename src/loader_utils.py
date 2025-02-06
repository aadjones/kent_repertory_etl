import json
import logging
import os

from processing_utils import prune_empty_keys
from text_utils import clean_filename

logger = logging.getLogger(__name__)


def save_chapter(chapter, output_dir="data/processed"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # Prune keys with empty outputs.
    pruned_chapter = prune_empty_keys(chapter)
    filename = f"chapter_{clean_filename(chapter.get('title', 'chapter'))}.json"
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w", encoding="utf-8") as outfile:
        json.dump(pruned_chapter, outfile, indent=2, ensure_ascii=False, sort_keys=False)
    logger.info(f"Chapter saved to {output_path}")

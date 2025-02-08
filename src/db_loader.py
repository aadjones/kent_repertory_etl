import json
import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Chapter, Page, Remedy, Rubric

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


def load_json(filepath):
    """Load the processed JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def insert_chapter(session, chapter_data):
    # Create a Chapter record.
    chapter = Chapter(
        title=chapter_data.get("title"),
        section=chapter_data.get("section"),
        pages_covered=chapter_data.get("page_info"),
    )
    session.add(chapter)
    session.flush()  # so that chapter.id gets assigned

    # If the chapter JSON uses a flat structure with rubrics that each have a 'page' attribute,
    # group them by that attribute.
    rubrics = chapter_data.get("rubrics", [])
    pages_dict = {}
    for rub in rubrics:
        page_marker = rub.get("page", "P1")
        pages_dict.setdefault(page_marker, []).append(rub)

    logger.info(f"Inserting chapter '{chapter.title}' with {len(pages_dict)} page group(s).")

    for page_marker, rub_list in pages_dict.items():
        page = Page(chapter_id=chapter.id, page=page_marker)
        session.add(page)
        session.flush()  # assign page.id
        # Insert each rubric from this page group.
        for rubric_data in rub_list:
            insert_rubric(session, rubric_data, page_id=page.id, parent_id=None)
    session.commit()
    logger.info(f"Inserted chapter '{chapter.title}' successfully.")


def insert_rubric(session, rubric_data, page_id, parent_id=None):
    related = rubric_data.get("related_rubrics", [])
    related_str = ",".join(related) if related else None

    rubric = Rubric(page_id=page_id, parent_id=parent_id, rubric=rubric_data.get("rubric"), related_rubrics=related_str)
    session.add(rubric)
    session.flush()

    for remedy_data in rubric_data.get("remedies", []):
        remedy = Remedy(rubric_id=rubric.id, name=remedy_data.get("name"), grade=remedy_data.get("grade"))
        session.add(remedy)

    for subrubric_data in rubric_data.get("subcontent", []):
        insert_rubric(session, subrubric_data, page_id=page_id, parent_id=rubric.id)


if __name__ == "__main__":
    # Define the directory where the database should be stored.
    db_dir = os.path.join("data", "db")
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created database directory: {db_dir}")

    db_filepath = os.path.join(db_dir, "kent_repertory.db")
    engine = create_engine(f"sqlite:///{db_filepath}", echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Adjust the filepath to your JSON file as needed.
    json_filepath = os.path.join("data", "processed", "kent0000.json")
    if not os.path.exists(json_filepath):
        logger.error(f"JSON file not found: {json_filepath}")
        exit(1)

    chapter_data = load_json(json_filepath)
    insert_chapter(session, chapter_data)

import logging
import re

from bs4 import BeautifulSoup, Tag

from remedy_parser import parse_remedy_list
from text_utils import clean_header, is_decorative, normalize_subject_title

logger = logging.getLogger(__name__)


def extract_related_rubrics(header):
    """
    Extracts the content inside parentheses from the header, removes HTML tags, strips
    any leading "See", and returns a list of related rubric names.
    """
    match = re.search(r"\(([^)]*)\)", header)
    if match:
        # Get the raw content inside the parentheses.
        raw_content = match.group(1).strip()
        # Use BeautifulSoup to remove any HTML tags.
        cleaned_text = BeautifulSoup(raw_content, "lxml").get_text(strip=True)
        # Remove a leading "See" if present.
        if cleaned_text.lower().startswith("see"):
            cleaned_text = cleaned_text[3:].strip()
        # Split on commas (if multiple related rubrics are provided).
        related = [x.strip() for x in cleaned_text.split(",") if x.strip()]
        return related
    return []


def merge_duplicate_rubrics(rubrics):
    merged = {}
    order = []
    for rub in rubrics:
        rub.setdefault("description", "")
        rub.setdefault("remedies", [])
        rub.setdefault("subrubrics", [])
        rub.setdefault("related_rubrics", [])
        title = rub.get("title", "").strip()
        key = title.lower()
        if key in merged:
            merged[key]["description"] += " " + rub.get("description", "")
            merged[key]["remedies"].extend(rub.get("remedies", []))
            merged[key]["subrubrics"].extend(rub.get("subrubrics", []))
            merged[key]["related_rubrics"].extend(rub.get("related_rubrics", []))
        else:
            merged[key] = rub.copy()
            order.append(key)
    for key in merged:
        merged[key]["description"] = merged[key]["description"].strip()
        unique_remedies = []
        seen = set()
        for remedy in merged[key]["remedies"]:
            remedy_key = (remedy.get("name"), remedy.get("grade"))
            if remedy_key not in seen:
                seen.add(remedy_key)
                unique_remedies.append(remedy)
        merged[key]["remedies"] = unique_remedies
        # Deduplicate related_rubrics preserving order.
        unique_related = []
        seen_related = set()
        for rel in merged[key]["related_rubrics"]:
            if rel not in seen_related:
                seen_related.add(rel)
                unique_related.append(rel)
        merged[key]["related_rubrics"] = unique_related
    logger.debug(f"Merged rubrics: {merged}")
    return [merged[k] for k in order]


def parse_directory(tag, level=0):
    """
    Recursively parse a <dir> tag to extract rubrics in a hierarchical structure.

    Each rubric is represented as a dictionary with keys:
      - title: Cleaned rubric title (parenthesized content removed)
      - related_rubrics: List of strings extracted from any parentheses in the header.
      - description: Text following a colon (if present), else empty.
      - remedies: List of remedy dictionaries.
      - subrubrics: List of child rubrics.

    A <p> is treated as a rubric header if it contains a colon, a <b> element,
    or if it contains parentheses (triggering extraction of related rubrics).
    Decorative entries (e.g. "---------->>>>>") are skipped.
    """
    rubrics = []
    current_rubric = None

    for child in tag.children:
        if isinstance(child, Tag):
            if child.name == "p":
                raw = child.decode_contents()
                if is_decorative(raw):
                    logger.debug("Skipping decorative content.")
                    continue

                logger.debug(f"Processing raw <p> content: {raw}")

                # NEW: Use colon check in addition to <b> tag and parentheses.
                if ":" in raw or child.find("b") or (len(extract_related_rubrics(raw)) > 0):
                    # Finish the previous rubric if any.
                    if current_rubric:
                        if not is_decorative(current_rubric["title"]):
                            rubrics.append(current_rubric)
                        current_rubric = None

                    if ":" in raw:
                        header_raw, remedy_raw = raw.split(":", 1)
                        # Extract related rubrics from header_raw before cleaning.
                        related = extract_related_rubrics(header_raw)
                        header_text = BeautifulSoup(header_raw, "lxml").get_text(strip=True)
                        header_clean = clean_header(header_text)
                        if is_decorative(header_clean):
                            logger.debug(f"Header '{header_clean}' is decorative; skipping.")
                            current_rubric = None
                            continue
                        description = BeautifulSoup(remedy_raw, "lxml").get_text(" ", strip=True)
                        remedies = parse_remedy_list(remedy_raw)
                        current_rubric = {
                            "title": header_clean,
                            "related_rubrics": related,
                            "remedies": remedies,
                            "description": description,
                            "subrubrics": [],
                        }
                    else:
                        header_text = BeautifulSoup(raw, "lxml").get_text(strip=True)
                        header_clean = clean_header(header_text)
                        if is_decorative(header_clean):
                            logger.debug(f"Header '{header_clean}' is decorative; skipping.")
                            current_rubric = None
                            continue
                        related = extract_related_rubrics(raw)
                        current_rubric = {
                            "title": header_clean,
                            "related_rubrics": related,
                            "remedies": [],
                            "description": "",
                            "subrubrics": [],
                        }
                    logger.debug(f"Created rubric: title='{current_rubric['title']}'")
                    logger.debug(f"related_rubrics={current_rubric['related_rubrics']}")
                else:
                    # No colon and no header indicator; treat this <p> as additional detail.
                    additional = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
                    if additional and not is_decorative(additional):
                        if current_rubric:
                            current_rubric["description"] += " " + additional
                        else:
                            current_rubric = {
                                "title": additional,
                                "related_rubrics": [],
                                "remedies": [],
                                "description": "",
                                "subrubrics": [],
                            }
            elif child.name == "dir":
                subrubrics = parse_directory(child, level + 1)
                if current_rubric:
                    current_rubric["subrubrics"].extend(subrubrics)
                else:
                    rubrics.extend(subrubrics)
            else:
                continue

    if current_rubric and not is_decorative(current_rubric["title"]):
        rubrics.append(current_rubric)
    return rubrics


def group_by_page(rubrics, subject_keyword="MIND"):
    """
    Group a flat list of rubric dictionaries into page groups based on boundaries.
    A rubric with title matching "MIND p. X" starts a new page.
    If no page boundaries are found, create a default page "P1".
    The resulting page dictionary will have keys:
      - page: the page marker (e.g., "P1")
      - content: the list of merged rubrics.
    """
    groups = []
    current_group = None
    page_pattern = re.compile(rf"^{subject_keyword}\s*p\.?\s*(\d+)", re.IGNORECASE)
    for rub in rubrics:
        title = rub.get("title", "")
        match = page_pattern.match(title)
        if match:
            page_num = match.group(1)
            current_group = {"page": f"P{page_num}", "rubrics": []}
            groups.append(current_group)
        else:
            if normalize_subject_title(title).upper() == subject_keyword.upper():
                continue
            if current_group is None:
                current_group = {"page": "P1", "rubrics": []}
                groups.append(current_group)
            current_group["rubrics"].append(rub)
    # Rename the key "rubrics" to "content" after merging duplicates.
    for group in groups:
        group["content"] = merge_duplicate_rubrics(group["rubrics"])
        del group["rubrics"]
    logger.info(f"Grouped into pages: {[g['page'] for g in groups]}")
    return groups


def transform_content(rubrics):
    """
    Transform a list of rubric dictionaries into the desired format:
      - Rename "title" to "rubric"
      - Remove "description" entirely
      - Preserve the "remedies" list
      - Recursively process nested rubrics, renaming the key for nested items to "subcontent"

    Returns a new list of dictionaries in the final schema.
    """
    transformed = []
    for rub in rubrics:
        new_rub = {
            "rubric": rub.get("title", "").strip(),
            "remedies": rub.get("remedies", []),
        }
        if rub.get("subrubrics"):
            # Instead of using "content" here, we use "subcontent" for nested items.
            new_rub["subcontent"] = transform_content(rub["subrubrics"])
        transformed.append(new_rub)
    return transformed

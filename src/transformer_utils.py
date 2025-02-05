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

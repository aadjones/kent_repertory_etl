def prune_empty_keys(data):
    """
    Recursively remove dictionary keys whose values are empty (lists, strings, dicts)
    and also remove any keys named 'description'.
    """
    if isinstance(data, dict):
        return {k: prune_empty_keys(v) for k, v in data.items() if k.lower() != "description" and v not in ([], "", {})}
    elif isinstance(data, list):
        return [prune_empty_keys(item) for item in data if item not in ([], "", {})]
    else:
        return data

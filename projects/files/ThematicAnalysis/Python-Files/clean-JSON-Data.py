# Python JSON Clean Tool

import json
from collections import defaultdict

# Constants
TOOL_INPUT_JSON = "json_files/tool.json"
TOOL_OUTPUT_JSON = "json_files/tool-clean.json"
TOOL_OUTPUT_JS = "json_files/toolJSON.js"
TOOL_KEYS_TO_SPLIT = ["Factors", "Catergories", "Sub Groups", "Groups", "Sub Catergories"]
TOOL_JSON_PREFIX = "jsonData"
TOOL_GROUP_BY_KEYS = ["ID", "Extracts"]
TOOL_SUB_KEY_FIELDS = ["Sub Groups", "Catergories", "Groups", "Sub Catergories", "Factors"]
TOOL_SUB_GROUP_KEY = "Wrapper"

THEMATIC_INPUT_JSON = "json_files/thematic_analysis.json"
THEMATIC_OUTPUT_JSON = "json_files/thematic_analysis_clean.json"
THEMATIC_OUTPUT_JS = "json_files/thematic_analysisJSON.js"
THEMATIC_KEYS_TO_SPLIT = ["Factors", "Groups", "Sub Groups", "Glossary Check"]
THEMATIC_JSON_PREFIX = "jsonDataThematic"
THEMATIC_GROUP_BY_KEYS = ["ID", "References", "Extracts", "Facts"]
THEMATIC_SUB_KEY_FIELDS = ["Sub Groups", "Groups", "Factors"]

RISK_INPUT_JSON = "json_files/risk_matrix.json"
RISK_OUTPUT_JSON = "json_files/risk_matrix_clean.json"
RISK_OUTPUT_JS = "json_files/risk_matrixJSON.js"
RISK_KEYS_TO_SPLIT = []
RISK_JSON_PREFIX = "jsonDataRisk"

SEPARATOR = "\n"
TEXT_REMOVE = ["\u00a0"]


def read_json(path):
    """Load JSON data from file."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} records from {path}")
    return data


def write_json(data, path):
    """Write JSON data to file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Wrote {len(data)} records to {path}")


def add_prefix_to_json(input_path, output_path, prefix):
    """Wrap JSON contents in a JS variable assignment and save."""
    with open(input_path, 'r', encoding='utf-8') as f:
        raw = f.read()
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"const {prefix} = {raw};")
    print(f"Prefixed JS written to: {output_path}")


def clean_text(text, to_remove, count_dict=None):
    """Remove unwanted characters from a string and optionally count them."""
    removed_total = 0
    # Loop through characters to remove and clean them from the text
    for r in to_remove:
        count = text.count(r)
        text = text.replace(r, "")
        removed_total += count
        # Optionally update a dictionary with removal counts
        if count_dict is not None:
            count_dict[r] = count_dict.get(r, 0) + count
    if removed_total > 0:
        print(f"Cleaned {removed_total} unwanted character(s) from text.")
    return text.strip()


def transform_fields_to_lists(data, keys_to_split, separator):
    """Split string fields into lists for specified keys."""
    print(f"Transforming fields: {keys_to_split}")
    total = 0
    # Loop through each item in the dataset & check key
    for item in data:
        for key in keys_to_split:
            # If the key exists and is a string, split it into a list
            if key in item and isinstance(item[key], str):
                parts = item[key].split(separator)
                item[key] = [p.strip() for p in parts if p.strip()]
                total += 1
    print(f"Total fields transformed: {total}")
    return data


def build_group_key(item, keys):
    """Construct a tuple group key from item based on given keys."""
    return tuple(item.get(k, '') for k in keys)


def assign_group_keys(group_entry, keys, values):
    """Assign key-value pairs from group key to the grouped entry."""
    for idx, k in enumerate(keys):
        group_entry[k] = values[idx]


def wrap_sub_keys(item, sub_key_fields):
    """Wrap aligned items from list fields into structured dictionaries."""
    # Extract lists from item for each sub_key_field
    lists = [item.get(k, []) if isinstance(item.get(k, []), list) else [] for k in sub_key_fields]
    if not any(lists):
        return []
    # Use the shortest list length to avoid index errors
    min_len = min(len(lst) for lst in lists if lst)
    wrapped = []
    # Build dictionaries from aligned list elements
    for i in range(min_len):
        entry = {field: lists[j][i] if i < len(lists[j]) else "" for j, field in enumerate(sub_key_fields)}
        wrapped.append(entry)
    return wrapped



def split_fields(entry, keys_to_split, separator, remove_chars):
    """Clean and split delimited text fields into lists."""
    for key in keys_to_split:
        if key in entry and isinstance(entry[key], str):
            cleaned = clean_text(entry[key], remove_chars)
            entry[key] = [s.strip() for s in cleaned.split(separator) if s.strip()]
    return entry


def clean_simple_list(data, keys_to_split, separator, remove_chars):
    """Clean and split string fields in a list of dictionaries."""
    print(f"Cleaning simple list fields: {keys_to_split}")
    count = 0
    for item in data:
        original = item.copy()
        item = split_fields(item, keys_to_split, separator, remove_chars)
        if item != original:
            count += 1
    print(f"Cleaned {count} items")
    return data


def transform_data(data):
    """Convert list of items to dict with numeric keys."""
    print("Transforming list to numbered keys")
    transformed = {i+1: item for i, item in enumerate(data)}
    print(f"Total items transformed: {len(transformed)}")
    return transformed


def main():
    """Run the full JSON cleaning pipeline."""
    print("=== Cleaning Tool JSON Processor ===\n")

    try:
        # Process Tool JSON: clean fields, group entries, and write output
        print("--- Processing Tool JSON ---")
        tool_data = read_json(TOOL_INPUT_JSON)
        tool_data = transform_fields_to_lists(tool_data, TOOL_KEYS_TO_SPLIT, SEPARATOR)

        grouped = defaultdict(dict)
        for item in tool_data:
            group_key = build_group_key(item, TOOL_GROUP_BY_KEYS)
            assign_group_keys(grouped[group_key], TOOL_GROUP_BY_KEYS, group_key)
            wrapped = wrap_sub_keys(item, TOOL_SUB_KEY_FIELDS)
            grouped[group_key].setdefault(TOOL_SUB_GROUP_KEY, []).extend(wrapped)

        grouped_tool_data = list(grouped.values())
        print(f"Total grouped entries: {len(grouped_tool_data)}")

        write_json(grouped_tool_data, TOOL_OUTPUT_JSON)
        add_prefix_to_json(TOOL_OUTPUT_JSON, TOOL_OUTPUT_JS, TOOL_JSON_PREFIX)
        print()
    except Exception as e:
        print(f"Error processing tool.json: {e}\n")

    try:
        # Process Thematic Analysis JSON: clean and export
        print("--- Processing Thematic Analysis JSON ---")
        thematic_data = read_json(THEMATIC_INPUT_JSON)
        thematic_data = clean_simple_list(thematic_data, THEMATIC_KEYS_TO_SPLIT, SEPARATOR, TEXT_REMOVE)
        write_json(thematic_data, THEMATIC_OUTPUT_JSON)
        add_prefix_to_json(THEMATIC_OUTPUT_JSON, THEMATIC_OUTPUT_JS, THEMATIC_JSON_PREFIX)
        print()
    except Exception as e:
        print(f"Error processing thematic_analysis.json: {e}\n")

    try:
        # Process Risk Matrix JSON: clean, transform, and export
        print("--- Processing Risk Matrix JSON ---")
        risk_data = read_json(RISK_INPUT_JSON)
        risk_data = clean_simple_list(risk_data, RISK_KEYS_TO_SPLIT, SEPARATOR, TEXT_REMOVE)
        transformed_data = transform_data(risk_data)
        write_json(transformed_data, RISK_OUTPUT_JSON)
        add_prefix_to_json(RISK_OUTPUT_JSON, RISK_OUTPUT_JS, RISK_JSON_PREFIX)
        print()
    except Exception as e:
        print(f"Error processing risk_matrix.json: {e}\n")

    print("=== Cleaning Complete ===")


if __name__ == "__main__":
    main()

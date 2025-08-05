# Python JSON clean tool

import json
from collections import defaultdict

# Define constants
INPUT_JSON_FILE = "json_files/QuizData.json"
OUTPUT_JSON_FILE = "json_files/QuizData-clean.json"
OUTPUT_JS_FILE = "json_files/QuizData-JSON.js"
KEYS_TO_SPLIT = ["Multiple Answers", "Correct Answer"]
JSON_PREFIX = "jsonData"
SEPARATOR = "\n"
SPECIFIC_TEXT_REMOVE = ["\u00a0"]
MAIN_KEY = "Module"
GROUP_BY_KEYS = ["Module", "Module Name"]
SUB_GROUP_BY_KEY = "Questions"
SUB_KEY_FIELDS = ["ID", "Question", "Multiple Answers", "Correct Answer", "Explanation"]


def read_json(file_path):
    """Read JSON data from file."""
    print(f"=== Reading Input File: {file_path} ===")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            json_data = json.load(file)
        print("Successfully read input JSON.\n")
        return json_data
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return None


def write_json(data, file_path):
    """Write JSON data to file."""
    print(f"=== Writing Cleaned JSON to: {file_path} ===")
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print("Cleaned JSON written successfully.\n")
    except Exception as e:
        print(f"Error writing JSON file: {e}")


def transform_field_to_list(data, fields_to_transform, separator):
    """Transform specified fields into lists."""
    print(f"=== Transforming Fields: {fields_to_transform} ===")
    total_transformed = 0

    # Loop through each specified field
    for field in fields_to_transform:
        transformed_count = 0
        for item in data:
            # Only process strings in those fields
            if field in item and isinstance(item[field], str):
                cleaned_field = item[field].replace('"', '').strip()
                # Split into list and clean whitespace
                item[field] = [x.strip() for x in cleaned_field.split(separator)]
                # Convert numeric strings to integers
                item[field] = [int(x) if x.isdigit() else x for x in item[field]]
                transformed_count += 1
        print(f"Field '{field}': {transformed_count} items transformed")
        total_transformed += transformed_count

    print(f"Total fields transformed across all fields {fields_to_transform}: {total_transformed}\n")
    return data


def group_data_by_keys(data, group_by_keys, sub_group_by_key, sub_key_fields):
    """Group data by specified keys and include only the specified fields."""
    print(f"=== Grouping data by keys: {group_by_keys} ===")
    grouped_data = defaultdict(lambda: {sub_group_by_key: []})

    # Iterate over all records and group by key tuple
    for item in data:
        group_key = tuple(item.get(key, '') for key in group_by_keys)
        entry = {field: item[field] for field in sub_key_fields}
        grouped_data[group_key][sub_group_by_key].append(entry)

    # Reconstruct grouped structure for output
    result = []
    for key, value in grouped_data.items():
        entry = {k: v for k, v in zip(group_by_keys, key)}
        entry[sub_group_by_key] = value[sub_group_by_key]
        result.append(entry)

    print(f"Total groups created using keys {group_by_keys}: {len(result)}\n")
    return result


def add_prefix_to_json(input_json_file, output_js_file, prefix):
    """Add a prefix to define a JSON file and save it as a .js file."""
    print(f"=== Adding Prefix and Saving as JS: {output_js_file} ===")
    try:
        with open(input_json_file, "r", encoding='utf-8') as file:
            json_data = file.read()
        prefixed_json_data = f"const {prefix} = {json_data};"
        with open(output_js_file, "w", encoding='utf-8') as file:
            file.write(prefixed_json_data)
        print("Prefixed .js file written successfully.\n")
    except Exception as e:
        print(f"Error adding prefix to JSON: {e}")


def clean_data(input_data):
    """Clean and transform the input data."""
    print("=== Starting Data Cleaning ===")
    processed_data = []
    item_count = 0

    # Flatten and sanitize each item in the input data
    for items in input_data.values():
        for item in items:
            processed_item = dict(item)
            original_value = item.get(MAIN_KEY)
            # Ensure MAIN_KEY is treated as a string (or integer if valid)
            processed_item[MAIN_KEY] = original_value if isinstance(original_value, int) else str(original_value)
            processed_data.append(processed_item)
            item_count += 1

    # Convert selected fields to lists and group cleaned records
    processed_data = transform_field_to_list(processed_data, KEYS_TO_SPLIT, SEPARATOR)
    grouped_data = group_data_by_keys(processed_data, GROUP_BY_KEYS, SUB_GROUP_BY_KEY, SUB_KEY_FIELDS)

    print(f"Total items processed: {item_count}")
    print("=== Data Cleaning Complete ===\n")
    return grouped_data


def main():
    print("=== JSON Cleaning Tool Started ===\n")

    # Load input JSON
    data = read_json(INPUT_JSON_FILE)
    if not data:
        print("Aborting: no data loaded.")
        return

    # Clean and group data
    grouped_data = clean_data(data)

    # Output cleaned JSON and JS-formatted version
    write_json(grouped_data, OUTPUT_JSON_FILE)
    add_prefix_to_json(OUTPUT_JSON_FILE, OUTPUT_JS_FILE, JSON_PREFIX)

    print("=== JSON Cleaning Tool Finished ===")



if __name__ == "__main__":
    main()

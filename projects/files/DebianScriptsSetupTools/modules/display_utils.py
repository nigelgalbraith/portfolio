#!/usr/bin/env python3
"""
display_utils.py

Utility functions for displaying formatted tables, summaries, and labeled lists
from dictionaries and lists. Useful for presenting job status, installation results,
and structured logs in CLI tools or terminal scripts.
"""

def format_status_summary(status_dict, label="Item", count_keys=None):
    """
    Returns a formatted summary of statuses in a dictionary, with row-wise display and totals.

    Args:
        status_dict (dict): Dictionary of {item_name: status}.
        label (str): Header label for the item column.
        count_keys (list or None): Optional list of keys to display in the summary section.

    Returns:
        str: Formatted multiline string.

    Example:
        result = {
            "pkg1": "INSTALLED",
            "pkg2": "MISSING",
            "pkg3": "INSTALLED"
        }
        print(format_status_summary(result, label="Package"))
    """
    lines = []
    lines.append(f"\n{label} Status Summary\n" + "-" * (len(label) + 16))
    lines.append(f"{label:<30}Status")
    lines.append(f"{'-' * len(label):<30}------")

    for item, status in status_dict.items():
        lines.append(f"{item:<30}{status}")

    # Count occurrences
    counts = {}
    for status in status_dict.values():
        counts[status] = counts.get(status, 0) + 1

    lines.append("\nSummary:\n--------")
    display_keys = count_keys if count_keys else sorted(counts.keys())
    for key in display_keys:
        lines.append(f"{key:<13}: {counts.get(key, 0)}")
    lines.append(f"Total        : {sum(counts.values())}")
    return "\n".join(lines)


def print_dict_table(items, field_names, label):
    """
    Print a table for a list of dictionaries with selected field columns.

    Args:
        items (list of dict): List of dictionaries containing the same fields.
        field_names (list): List of keys to display as columns.
        label (str): Label for the table section.

    Example:
        jobs = [
            {"name": "pkg1", "status": "INSTALLED"},
            {"name": "pkg2", "status": "MISSING"}
        ]
        print_dict_table(jobs, ["name", "status"], "APT Packages")
    """
    if not items:
        print(f"\n{label.upper()}: (None)")
        return

    print(f"\n{label.upper()}:")
    col_widths = [max(len(field), 12) for field in field_names]

    # Header
    print("  " + "  ".join(f"{field:<{col_widths[i]}}" for i, field in enumerate(field_names)))
    print("  " + "  ".join("-" * col_widths[i] for i in range(len(field_names))))

    # Rows
    for item in items:
        print("  " + "  ".join(f"{str(item.get(field, '')):<{col_widths[i]}}" for i, field in enumerate(field_names)))


def print_list_section(items, label):
    """
    Print a list of strings under a label with bullet points.

    Args:
        items (list of str): List of strings to display.
        label (str): Section label for the list.

    Example:
        print_list_section(["curl", "git", "vim"], "Installed Tools")
    """
    print(f"\n{label.upper()}:")
    for item in items:
        print(f"  - {item}")

#!/usr/bin/env python3
"""
display_utils.py

Utility functions for displaying formatted tables, summaries, and labeled lists
from dictionaries and lists. Useful for presenting job status, installation results,
and structured logs in CLI tools or terminal scripts.
"""

from typing import Dict, Any, Optional

def format_status_summary(
    status_dict: Dict[str, Any],
    label: str = "Item",
    count_keys: Optional[list] = None,
    labels: Optional[Dict[Any, str]] = None,
) -> str:
    """
    Returns a formatted summary of statuses in a dictionary, with row-wise display and totals.

    Args:
        status_dict: {item_name: status}; status may be bool or string.
        label: Header label for the item column.
        count_keys: Optional list of label strings to force order of summary lines.
        labels: Optional mapping from raw status -> display string (e.g., {True: "INSTALLED", False: "UNINSTALLED"}).

    Returns:
        str: Formatted multiline string.
    """
    # Default mapping if caller doesn't pass one
    labels = labels or {True: "INSTALLED", False: "NOT INSTALLED"}

    # Compute column width dynamically
    max_item_len = max([len(label)] + [len(str(item)) for item in status_dict.keys()])
    col_width = max_item_len + 4  # add padding

    # Build header
    lines = []
    title = f"{label} Status Summary"
    lines.append(f"\n{title}\n" + "-" * len(title))
    lines.append(f"{label:<{col_width}}Status")
    lines.append(f"{'-' * len(label):<{col_width}}------")

    # Row display using mapping when possible
    for item, status in status_dict.items():
        display_status = labels.get(status, str(status))
        lines.append(f"{item:<{col_width}}{display_status}")

    # Count occurrences using display labels
    counts: Dict[str, int] = {}
    for status in status_dict.values():
        display_status = labels.get(status, str(status))
        counts[display_status] = counts.get(display_status, 0) + 1

    # Summary section
    lines.append("\nSummary:\n--------")
    display_keys = count_keys if count_keys else sorted(counts.keys())
    for key in display_keys:
        lines.append(f"{key:<13}: {counts.get(key, 0)}")
    lines.append(f"Total        : {sum(counts.values())}")

    return "\n".join(lines)


def print_dict_table(items, field_names, label):
    """
    Print a table for a list of dicts with dynamic column widths.
    If a cell value is a list, the column width is based on the longest element
    (i.e., the longest line you'll print), not the entire list representation.
    """
    if not items:
        print(f"\n{label.upper()}: (None)")
        return

    def value_display_len(v):
        if isinstance(v, list):
            return max((len(str(x)) for x in v), default=0)
        return len(str(v))

    # Column widths based on header vs longest display value (list-aware)
    col_widths = []
    for field in field_names:
        max_len = max(value_display_len(item.get(field, "")) for item in items)
        col_widths.append(max(len(field), max_len) + 2)  # padding

    print(f"\n{label.upper()}:")
    # Header
    print("  " + "  ".join(f"{field:<{col_widths[i]}}" for i, field in enumerate(field_names)))
    print("  " + "  ".join("-" * col_widths[i] for i in range(len(field_names))))

    # Rows (support multi-line for lists)
    for item in items:
        # Build per-column lines
        columns = []
        for i, field in enumerate(field_names):
            val = item.get(field, "")
            if isinstance(val, list):
                lines = [str(v) for v in val]
            else:
                lines = [str(val)]

            # Truncate each line to column width (if needed)
            wrapped = []
            for line in lines:
                if len(line) > col_widths[i]:
                    line = line[: col_widths[i] - 3] + "..."
                wrapped.append(f"{line:<{col_widths[i]}}")
            columns.append(wrapped)

        # Max number of lines in this row
        max_lines = max(len(col) for col in columns)

        # Print the row line-by-line
        for j in range(max_lines):
            row_parts = []
            for i, col in enumerate(columns):
                if j < len(col):
                    row_parts.append(col[j])
                else:
                    row_parts.append(" " * col_widths[i])
            print("  " + "  ".join(row_parts))



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


def select_from_list(title: str, options: list[str]) -> str | None:
    """
    Render a simple 1..N chooser and return the selected option (or None).

    Args:
        title (str): Section title to print above options.
        options (list[str]): Options to display.

    Example:
        >>> select_from_list("Run which game", ["Duke", "Keen"])
        "Duke"
    """
    if not options:
        return None
    print(f"\n{title}:")
    for i, opt in enumerate(options, start=1):
        print(f"{i}) {opt}")
    try:
        idx = int(input(f"Enter your selection (1-{len(options)}): ").strip())
    except ValueError:
        return None
    return options[idx - 1] if 1 <= idx <= len(options) else None


# ...existing imports / functions...

def confirm(
    prompt: str = "Proceed? [y/n]: ",
    *,
    valid_yes: tuple[str, ...] = ("y", "yes"),
    valid_no: tuple[str, ...] = ("n", "no")
) -> bool:
    """
    Prompt user for a yes/no answer until valid input is provided.
    No defaults — the user must type y/yes or n/no.

    Args:
        prompt: Text to show the user (include your own [y/n] hint).
        valid_yes: Accepted tokens for "yes" (case-insensitive).
        valid_no: Accepted tokens for "no" (case-insensitive).

    Returns:
        True for yes, False for no.
    """
    yes = tuple(s.lower() for s in valid_yes)
    no  = tuple(s.lower() for s in valid_no)

    while True:
        resp = input(prompt).strip().lower()
        if resp in yes:
            return True
        if resp in no:
            return False
        print(f"Invalid input. Please enter one of: {', '.join(valid_yes + valid_no)}.")






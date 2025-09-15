#!/usr/bin/env python3
"""
display_utils.py
"""

from typing import Dict, Any, Optional
import os
import getpass

def format_status_summary(status_dict: Dict[str, Any], label: str = "Item", count_keys: Optional[list] = None, labels: Optional[Dict[Any, str]] = None) -> str:
    """Return a formatted summary of statuses in a dictionary."""
    labels = labels or {True: "INSTALLED", False: "NOT INSTALLED"}
    max_item_len = max([len(label)] + [len(str(item)) for item in status_dict.keys()])
    col_width = max_item_len + 4
    lines = []
    title = f"{label} Status Summary"
    lines.append(f"\n{title}\n" + "-" * len(title))
    lines.append(f"{label:<{col_width}}Status")
    lines.append(f"{'-' * len(label):<{col_width}}------")
    for item, status in status_dict.items():
        display_status = labels.get(status, str(status))
        lines.append(f"{item:<{col_width}}{display_status}")
    counts: Dict[str, int] = {}
    for status in status_dict.values():
        display_status = labels.get(status, str(status))
        counts[display_status] = counts.get(display_status, 0) + 1
    lines.append("\nSummary:\n--------")
    display_keys = count_keys if count_keys else sorted(counts.keys())
    for key in display_keys:
        lines.append(f"{key:<13}: {counts.get(key, 0)}")
    lines.append(f"Total        : {sum(counts.values())}")
    return "\n".join(lines)


def print_dict_table(items, field_names, label):
    """Print a table for a list of dicts with dynamic column widths."""
    if not items:
        print(f"\n{label.upper()}: (None)")
        return
    def value_display_len(v):
        if isinstance(v, list):
            return max((len(str(x)) for x in v), default=0)
        return len(str(v))
    col_widths = []
    for field in field_names:
        max_len = max(value_display_len(item.get(field, "")) for item in items)
        col_widths.append(max(len(field), max_len) + 2)
    print(f"\n{label.upper()}:")
    print("  " + "  ".join(f"{field:<{col_widths[i]}}" for i, field in enumerate(field_names)))
    print("  " + "  ".join("-" * col_widths[i] for i in range(len(field_names))))
    for item in items:
        columns = []
        for i, field in enumerate(field_names):
            val = item.get(field, "")
            if isinstance(val, list):
                lines = [str(v) for v in val]
            else:
                lines = [str(val)]
            wrapped = []
            for line in lines:
                if len(line) > col_widths[i]:
                    line = line[: col_widths[i] - 3] + "..."
                wrapped.append(f"{line:<{col_widths[i]}}")
            columns.append(wrapped)
        max_lines = max(len(col) for col in columns)
        for j in range(max_lines):
            row_parts = []
            for i, col in enumerate(columns):
                if j < len(col):
                    row_parts.append(col[j])
                else:
                    row_parts.append(" " * col_widths[i])
            print("  " + "  ".join(row_parts))


def print_list_section(items, label):
    """Print a list of strings under a label with bullet points."""
    print(f"\n{label.upper()}:")
    for item in items:
        print(f"  - {item}")


def select_from_list(title: str, options: list[str]) -> str | None:
    """Render a simple chooser and return the selected option or None."""
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


def pick_constants_interactively(choices: dict[str, tuple[str, Optional[int]]]) -> str:
    """Show a simple menu to choose constants module, filtered by allowed UID."""
    current_uid = os.geteuid()
    current_user = getpass.getuser()
    allowed = {label: mod for label, (mod, uid) in choices.items() if uid is None or uid == current_uid}
    disallowed = {label: (mod, uid) for label, (mod, uid) in choices.items() if uid is not None and uid != current_uid}
    if disallowed:
        print("\n--- Programs not available for this user ---")
        for label, (_, uid) in disallowed.items():
            print(f"  [{'root only' if uid == 0 else f'uid {uid} only'}] {label}")
        print("-------------------------------------------\n")
    if not allowed:
        raise SystemExit(f"[FATAL] No utilities available for user '{current_user}' (uid {current_uid})")
    options = list(allowed.keys()) + ["Exit"]
    print("\nChoose a utility")
    for i, opt in enumerate(options, 1):
        print(f"{i}) {opt}")
    choice = input(f"Enter your selection (1-{len(options)}): ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(options)):
        raise SystemExit("Invalid selection.")
    selection = options[int(choice) - 1]
    if selection == "Exit":
        raise SystemExit("Exited by user.")
    return allowed[selection]


def confirm(prompt: str = "Proceed? [y/n]: ", *, valid_yes: tuple[str, ...] = ("y", "yes"), valid_no: tuple[str, ...] = ("n", "no")) -> bool:
    """Prompt user for a yes/no answer until valid input is provided."""
    yes = tuple(s.lower() for s in valid_yes)
    no = tuple(s.lower() for s in valid_no)
    while True:
        resp = input(prompt).strip().lower()
        if resp in yes:
            return True
        if resp in no:
            return False
        print(f"Invalid input. Please enter one of: {', '.join(valid_yes + valid_no)}.")

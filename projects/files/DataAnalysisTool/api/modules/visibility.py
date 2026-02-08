"""Centralized UX visibility rules.

These filters are for UI cleanliness (not security). If a client explicitly
addresses a hidden database/table by name, the backend can still serve it.

Keeping these rules in one place avoids duplicated filtering logic across routes.
"""

# Databases that should not show up in the UI picker.
HIDDEN_DATABASES = {"postgres", "dataanalysis"}

# Tables that should not be exposed in UI table lists.
HIDDEN_TABLES = {"_tool_table_meta"}


def is_hidden_database(name: str) -> bool:
    """Return True if a database name should be hidden from UI lists."""
    return name in HIDDEN_DATABASES


def is_hidden_table(name: str) -> bool:
    """Return True if a table name should be hidden from UI lists."""
    return name in HIDDEN_TABLES

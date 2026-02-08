"""Per-table tool metadata stored inside each target database.

This module provides helpers for ensuring the metadata table exists and for
reading/writing per-table settings like table role (entity/lookup/junction).

Routes should remain thin and call into this module.
"""

from __future__ import annotations

from typing import Any

from modules.db import exec_sql, fetch_all


META_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public._tool_table_meta (
  table_name    TEXT PRIMARY KEY,
  table_type    TEXT NOT NULL CHECK (table_type IN ('entity','lookup','junction')),
  label_column  TEXT,
  junction_mode TEXT CHECK (junction_mode IN ('simple','with_data')),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def ensure_meta_table(db: str) -> None:
    """Ensure the tool metadata table exists in the target database."""
    exec_sql(db, META_TABLE_SQL)


def seed_meta_rows(db: str, table_names: list[str]) -> None:
    """Insert default meta rows for tables that don't have one yet."""
    if not table_names:
        return
    sql = """
    INSERT INTO public._tool_table_meta (table_name, table_type)
    VALUES (%s, 'entity')
    ON CONFLICT (table_name) DO NOTHING
    """
    for t in table_names:
        exec_sql(db, sql, (t,))


def fetch_table_meta(db: str) -> dict[str, dict[str, Any]]:
    """Return the current table meta mapping."""
    ensure_meta_table(db)
    meta_rows = fetch_all(
        db,
        """
        SELECT table_name, table_type, label_column, junction_mode
        FROM public._tool_table_meta
        ORDER BY table_name
        """,
    )
    return {
        r["table_name"]: {
            "tableType": r["table_type"],
            "labelColumn": r["label_column"],
            "junctionMode": r["junction_mode"],
        }
        for r in meta_rows
    }


def upsert_table_meta(
    db: str,
    *,
    table_name: str,
    table_type: str,
    label_column: str | None = None,
    junction_mode: str | None = None,
) -> None:
    """Upsert per-table metadata (role/label/junction mode)."""
    ensure_meta_table(db)
    exec_sql(
        db,
        """
        INSERT INTO public._tool_table_meta (table_name, table_type, label_column, junction_mode, updated_at)
        VALUES (%s, %s, %s, %s, now())
        ON CONFLICT (table_name) DO UPDATE
          SET table_type = EXCLUDED.table_type,
              label_column = EXCLUDED.label_column,
              junction_mode = EXCLUDED.junction_mode,
              updated_at = now()
        """,
        (table_name, table_type, label_column, junction_mode),
    )

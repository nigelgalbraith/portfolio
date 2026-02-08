import datetime
import re

import psycopg2
import psycopg2.extras

from flask import abort

from modules.db import fetch_all, fetch_one, exec_sql, pg_conn
from modules.validators import require_ident, qident


def get_primary_key_columns(db: str, table: str) -> list[str]:
    """Return primary key column names for a public table."""
    rows = fetch_all(
        db,
        """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = 'public'
          AND tc.table_name = %s
          AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position
        """,
        (table,),
    )
    return [r["column_name"] for r in rows]


def get_table_column_meta(db: str, table: str) -> list[dict]:
    """Return column metadata from information_schema for a public table."""
    return fetch_all(
        db,
        """
        SELECT
          column_name,
          data_type,
          is_nullable,
          column_default,
          is_identity,
          COALESCE(is_generated, 'NEVER') AS is_generated,
          character_maximum_length
        FROM information_schema.columns
        WHERE table_schema='public'
          AND table_name=%s
        ORDER BY ordinal_position
        """,
        (table,),
    )


def compute_required_columns(col_rows: list[dict]) -> set[str]:
    """Columns required for inserts without defaults or generated values."""
    required = set()
    for r in col_rows:
        name = r["column_name"]
        is_nullable = (r.get("is_nullable") or "YES").upper()
        has_default = r.get("column_default") is not None
        is_identity = (r.get("is_identity") or "NO").upper() == "YES"
        is_generated = (r.get("is_generated") or "NEVER").upper() != "NEVER"
        if is_nullable == "NO" and (not has_default) and (not is_identity) and (not is_generated):
            required.add(name)
    return required


def _is_iso_date(s: str) -> bool:
    """Best-effort ISO-8601 date/time validation."""
    try:
        # Accept date or datetime
        datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except Exception:
        return False


def validate_values(db: str, table: str, values: dict, *, mode: str) -> None:
    """Validate value types and constraints using information_schema metadata."""
    if not isinstance(values, dict):
        abort(400, "values must be an object")
    if mode not in {"create", "update"}:
        abort(400, "Invalid validation mode")
    col_rows = get_table_column_meta(db, table)
    meta_by_col = {r["column_name"]: r for r in col_rows}
    for k, v in values.items():
        col = require_ident(k, "column")
        if col not in meta_by_col:
            abort(400, f"Unknown column: {col}")
        meta = meta_by_col[col]
        data_type = (meta.get("data_type") or "").lower()
        max_len = meta.get("character_maximum_length")
        is_nullable = (meta.get("is_nullable") or "YES").upper() == "YES"
        # Null handling
        if v is None:
            if not is_nullable:
                abort(400, f"Column '{col}' cannot be null")
            continue
        # String length
        if max_len is not None and isinstance(v, str) and len(v) > int(max_len):
            abort(400, f"Column '{col}' exceeds max length {max_len}")
        # Basic type sanity
        if data_type in {"integer", "smallint", "bigint"}:
            if isinstance(v, bool):
                abort(400, f"Column '{col}' must be an integer")
            if isinstance(v, int):
                continue
            if isinstance(v, str) and re.fullmatch(r"[+-]?\d+", v.strip()):
                continue
            abort(400, f"Column '{col}' must be an integer")
        if data_type in {"numeric", "decimal", "real", "double precision"}:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                continue
            if isinstance(v, str) and re.fullmatch(r"[+-]?(\d+)(\.\d+)?", v.strip()):
                continue
            abort(400, f"Column '{col}' must be a number")
        if data_type == "boolean":
            if isinstance(v, bool):
                continue
            if isinstance(v, int) and v in (0, 1):
                continue
            if isinstance(v, str) and v.strip().lower() in {"true", "false", "t", "f", "0", "1", "yes", "no"}:
                continue
            abort(400, f"Column '{col}' must be a boolean")
        if data_type in {"date", "timestamp without time zone", "timestamp with time zone", "time without time zone", "time with time zone"}:
            if isinstance(v, str) and _is_iso_date(v.strip()):
                continue
            # allow pg to parse some strings, but keep basic sanity
            abort(400, f"Column '{col}' must be an ISO date/time string")
        # character/text types: accept anything coercible to string
        if data_type in {"character varying", "character", "text", "uuid"}:
            if isinstance(v, (str, int, float)) and not isinstance(v, bool):
                continue
            abort(400, f"Column '{col}' must be text")
        # For other types (json, arrays, etc.), skip strict validation for now.
        # The DB will enforce correct casts/constraints.


def build_where_clause(filters: dict) -> tuple[str, list]:
    """Build a parameterized WHERE clause from column filters."""
    clauses, params = [], []
    for k, v in (filters or {}).items():
        col = require_ident(k, "column")
        clauses.append(f"{qident(col, 'column')} = %s")
        params.append(v)
    if not clauses:
        return "", []
    return " WHERE " + " AND ".join(clauses), params


def _create_record(db: str, table: str, values: dict):
    """Create a new record and return PK values plus required columns."""
    pk_cols = get_primary_key_columns(db, table)
    col_rows = get_table_column_meta(db, table)
    # Validate before building SQL (length/type/nullability)
    validate_values(db, table, values or {}, mode="create")
    allowed = {r["column_name"] for r in col_rows}
    identity_cols = {r["column_name"] for r in col_rows if (r.get("is_identity") or "NO").upper() == "YES"}
    required_cols = compute_required_columns(col_rows)
    clean_values = {}
    for k, v in (values or {}).items():
        col = require_ident(k, "column")
        if col not in allowed:
            abort(400, f"Unknown column: {col}")
        clean_values[col] = v
    insert_cols = [c for c in clean_values if c not in identity_cols]
    missing_required = sorted([c for c in required_cols if c not in insert_cols])
    if missing_required:
        abort(400, f"Missing required fields: {', '.join(missing_required)}")
    # CASE 1: identity-only insert
    if not insert_cols:
        sql = f"INSERT INTO {qident(table)} DEFAULT VALUES"
        if pk_cols:
            sql += " RETURNING " + ", ".join(qident(c) for c in pk_cols)
        with pg_conn(db) as cn:
            with cn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                ret = cur.fetchone() if pk_cols else None
        return ret or {}, required_cols
    cols_sql = ", ".join(qident(c) for c in insert_cols)
    vals_sql = ", ".join(["%s"] * len(insert_cols))
    params = [clean_values[c] for c in insert_cols]
    sql = f"INSERT INTO {qident(table)} ({cols_sql}) VALUES ({vals_sql})"
    if pk_cols:
        sql += " RETURNING " + ", ".join(qident(c) for c in pk_cols)
    with pg_conn(db) as cn:
        with cn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            ret = cur.fetchone() if pk_cols else None
    return ret or {}, required_cols


def _update_record(db: str, table: str, pk: dict, values: dict):
    """Update an existing record and return its PK values."""
    pk_cols = get_primary_key_columns(db, table)
    if not pk_cols:
        abort(400, "Table has no primary key; cannot update safely.")
    if not isinstance(pk, dict) or not pk:
        abort(400, "pk object required")
    missing = [c for c in pk_cols if c not in pk]
    if missing:
        abort(400, f"Missing pk columns: {', '.join(missing)}")
    col_rows = get_table_column_meta(db, table)
    allowed = {r["column_name"] for r in col_rows}
    # Validate before building SQL (length/type/nullability)
    validate_values(db, table, values or {}, mode="update")
    clean_values = {}
    for k, v in (values or {}).items():
        col = require_ident(k, "column")
        if col not in allowed:
            abort(400, f"Unknown column: {col}")
        clean_values[col] = v
    set_cols = [c for c in clean_values if c not in pk_cols]
    if not set_cols:
        abort(400, "No non-PK fields to update")
    set_sql = ", ".join(f"{qident(c)}=%s" for c in set_cols)
    params = [clean_values[c] for c in set_cols]
    where_sql, where_params = build_where_clause({c: pk[c] for c in pk_cols})
    params.extend(where_params)
    sql = f"UPDATE {qident(table)} SET {set_sql}{where_sql}"
    exec_sql(db, sql, params)
    return {c: pk[c] for c in pk_cols}


def get_junction_selections(
    db: str,
    junction_table: str,
    main_fk_column: str,
    main_id,
    far_fk_column: str,
) -> list:
    """Return far-side ids for a junction row set."""
    junction_table = require_ident(junction_table, "junction table")
    main_fk_column = require_ident(main_fk_column, "main fk column")
    far_fk_column = require_ident(far_fk_column, "far fk column")
    sql = f"""
      SELECT {qident(far_fk_column,'column')} AS v
      FROM {qident(junction_table,'table')}
      WHERE {qident(main_fk_column,'column')} = %s
      ORDER BY 1
    """
    rows = fetch_all(db, sql, (main_id,))
    return [r["v"] for r in rows]


def apply_junction_selections(
    db: str,
    junction_table: str,
    main_fk_column: str,
    main_id,
    far_fk_column: str,
    far_ids: list,
) -> None:
    """Sync junction rows so far_ids match the main record."""
    junction_table = require_ident(junction_table, "junction table")
    main_fk_column = require_ident(main_fk_column, "main fk column")
    far_fk_column = require_ident(far_fk_column, "far fk column")
    if not isinstance(far_ids, list):
        abort(400, "farIds must be an array")
    existing = get_junction_selections(
        db, junction_table, main_fk_column, main_id, far_fk_column
    )
    existing_map = {str(v): v for v in existing}
    desired_map = {str(v): v for v in far_ids if v is not None}
    to_remove = [existing_map[k] for k in existing_map.keys() if k not in desired_map]
    to_add = [desired_map[k] for k in desired_map.keys() if k not in existing_map]
    if to_remove:
        placeholders = ", ".join(["%s"] * len(to_remove))
        sql = (
            f"DELETE FROM {qident(junction_table,'table')}"
            f" WHERE {qident(main_fk_column,'column')} = %s"
            f" AND {qident(far_fk_column,'column')} IN ({placeholders})"
        )
        exec_sql(db, sql, tuple([main_id] + to_remove))
    if to_add:
        sql = (
            f"INSERT INTO {qident(junction_table,'table')}"
            f" ({qident(main_fk_column,'column')}, {qident(far_fk_column,'column')})"
            " VALUES (%s, %s)"
        )
        for v in to_add:
            exec_sql(db, sql, (main_id, v))

from flask import Blueprint, request, abort

from modules.validators import require_ident, qident
from modules.db import fetch_all, exec_sql, pg_conn
from modules.responses import ok_response
from modules.visibility import is_hidden_table
from modules.sql_utils import split_sql_statements
from modules.backups import backup_database

bp = Blueprint("tables", __name__)


@bp.get("/api/databases/<db>/tables")
def list_tables_rest(db):
    """List visible tables in a database."""
    db = require_ident(db, "db")
    rows = fetch_all(
        db,
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        """,
    )
    return ok_response(
        [
            {"id": r["table_name"], "label": r["table_name"]}
            for r in rows
            if not is_hidden_table(r["table_name"])
        ]
    )


@bp.post("/api/databases/<db>/tables")
def create_table_rest(db):
    """Create a new table with an identity primary key."""
    db = require_ident(db, "db")
    backup_database(db, reason="before create_table")
    data = request.json or {}
    table = require_ident(data.get("table", ""), "table")
    exec_sql(db, f"CREATE TABLE {qident(table)} (id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY)")
    return ok_response(None)


@bp.delete("/api/databases/<db>/tables/<table>")
def delete_table_rest(db, table):
    """Delete a table if it is empty of extra columns and references."""
    db = require_ident(db, "db")
    backup_database(db, reason="before delete_table")
    table = require_ident(table, "table")
    # Guard 1: only allow deleting "empty" tables (only 'id' column)
    col_rows = fetch_all(
        db,
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        """,
        (table,),
    )
    cols = {r["column_name"] for r in col_rows}
    if cols - {"id"}:
        abort(400, f"Refusing to delete '{table}': table has columns other than 'id'")
    # Guard 2: block if other tables have FKs referencing this table
    fk_rows = fetch_all(
        db,
        """
        SELECT kcu.table_name AS from_table,
               kcu.column_name AS from_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.table_schema = 'public'
          AND tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name = %s
        """,
        (table,),
    )
    if fk_rows:
        refs = ", ".join(f"{r['from_table']}.{r['from_column']}" for r in fk_rows[:5])
        more = "" if len(fk_rows) <= 5 else f" (+{len(fk_rows)-5} more)"
        abort(400, f"Refusing to delete '{table}': referenced by {refs}{more}")
    exec_sql(db, f"DROP TABLE {qident(table)}")
    return ok_response(None)


@bp.post("/api/databases/<db>/tables/import")
def import_tables_rest(db):
    """Import SQL statements from an uploaded file."""
    db = require_ident(db, "db")
    f = request.files.get("file")
    if not f:
        abort(400, "Missing SQL file")
    sql_text = f.read().decode("utf-8", errors="replace")
    try:
        with pg_conn(db) as cn:
            with cn.cursor() as cur:
                for stmt in split_sql_statements(sql_text):
                    cur.execute(stmt)
        return ok_response(None)
    except Exception as e:
        abort(400, f"Import failed: {e}")


@bp.post("/api/databases/<db>/junctions")
def create_junction_rest(db):
    """Create a junction table with composite primary key."""
    db = require_ident(db, "db")
    backup_database(db, reason="before create_junction")
    data = request.json or {}
    table = require_ident(data.get("table", ""), "table")
    left_table = require_ident(data.get("leftTable", ""), "leftTable")
    right_table = require_ident(data.get("rightTable", ""), "rightTable")
    left_pk = require_ident(data.get("leftPk", ""), "leftPk")
    right_pk = require_ident(data.get("rightPk", ""), "rightPk")
    left_col = require_ident(data.get("leftCol", ""), "leftCol")
    right_col = require_ident(data.get("rightCol", ""), "rightCol")
    on_delete_a = (data.get("onDeleteA") or "RESTRICT").upper()
    on_update_a = (data.get("onUpdateA") or "RESTRICT").upper()
    on_delete_b = (data.get("onDeleteB") or "RESTRICT").upper()
    on_update_b = (data.get("onUpdateB") or "RESTRICT").upper()
    allowed = {"RESTRICT", "CASCADE", "SET NULL", "NO ACTION"}
    if on_delete_a not in allowed or on_update_a not in allowed or on_delete_b not in allowed or on_update_b not in allowed:
        abort(400, "Invalid FK rule")
    # Create junction table (NO id; composite PK)
    exec_sql(
        db,
        f"""
        CREATE TABLE {qident(table)} (
          {qident(left_col)} BIGINT NOT NULL,
          {qident(right_col)} BIGINT NOT NULL,
          PRIMARY KEY ({qident(left_col)}, {qident(right_col)}),
          FOREIGN KEY ({qident(left_col)})
            REFERENCES {qident(left_table)}({qident(left_pk)})
            ON DELETE {on_delete_a}
            ON UPDATE {on_update_a},
          FOREIGN KEY ({qident(right_col)})
            REFERENCES {qident(right_table)}({qident(right_pk)})
            ON DELETE {on_delete_b}
            ON UPDATE {on_update_b}
        );
        """,
    )
    # Seed/ensure UI meta role
    exec_sql(
        db,
        """
        INSERT INTO public._tool_table_meta (table_name, table_type)
        VALUES (%s, 'junction')
        ON CONFLICT (table_name) DO UPDATE
          SET table_type = EXCLUDED.table_type, updated_at = now()
        """,
        (table,),
    )
    return ok_response(None)


@bp.delete("/api/databases/<db>/junctions/<table>")
def delete_junction_rest(db, table):
    """Delete a junction table and its metadata entry."""
    db = require_ident(db, "db")
    backup_database(db, reason="before delete_junction")
    table = require_ident(table, "table")
    # Guard 1: must be marked as a junction in _tool_table_meta
    meta_rows = fetch_all(
        db,
        """
        SELECT table_type
        FROM public._tool_table_meta
        WHERE table_name = %s
        """,
        (table,),
    )
    if not meta_rows or meta_rows[0]["table_type"] != "junction":
        abort(400, f"Refusing to delete '{table}': not marked as junction in _tool_table_meta")
    # Drop the junction table (should succeed if nothing else references it)
    exec_sql(db, f"DROP TABLE {qident(table)}")
    # Clean up meta row (optional but sane)
    exec_sql(
        db,
        "DELETE FROM public._tool_table_meta WHERE table_name = %s",
        (table,),
    )
    return ok_response(None)

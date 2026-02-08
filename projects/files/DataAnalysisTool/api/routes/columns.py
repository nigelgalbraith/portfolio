from flask import Blueprint, request, abort

from modules.validators import require_ident, qident
from modules.db import fetch_all, exec_sql
from modules.responses import ok_response
from modules.backups import backup_database

bp = Blueprint("columns", __name__)


@bp.get("/api/databases/<db>/tables/<table>/columns")
def list_columns_rest(db, table):
    """Return the column list for a table."""
    db = require_ident(db, "db")
    table = require_ident(table, "table")
    rows = fetch_all(
        db,
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return ok_response([{"name": r["column_name"], "type": r["data_type"]} for r in rows])


@bp.post("/api/databases/<db>/tables/<table>/columns")
def create_column_rest(db, table):
    """Create a new column on a table."""
    db = require_ident(db, "db")
    backup_database(db, reason="before create_column")
    table = require_ident(table, "table")
    data = request.json or {}
    col = require_ident(data.get("name", ""), "column")
    ctype = (data.get("type") or "").strip()
    if not ctype:
        abort(400, "Column type required")
    exec_sql(db, f"ALTER TABLE {qident(table)} ADD COLUMN {qident(col)} {ctype}")
    return ok_response(None)


@bp.delete("/api/databases/<db>/tables/<table>/columns/<column>")
def delete_column_rest(db, table, column):
    """Delete a table column if it is safe to drop."""
    db = require_ident(db, "db")
    backup_database(db, reason="before delete_column")
    table = require_ident(table, "table")
    column = require_ident(column, "column")
    # 1) Never allow dropping the conventional PK column
    if column == "id":
        abort(400, "Cannot delete primary key column 'id'")
    # 2) Block dropping any primary-key column (composite PKs too)
    pk_rows = fetch_all(
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
        """,
        [table],
    )
    pk_cols = {r["column_name"] for r in pk_rows}
    if column in pk_cols:
        abort(400, f"Cannot delete primary key column '{column}'")
    # 3) Block dropping columns referenced by FKs (incoming)
    fk_rows = fetch_all(
        db,
        """
        SELECT tc.table_name AS from_table,
               kcu.column_name AS from_column,
               ccu.table_name AS to_table,
               ccu.column_name AS to_column
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
          AND ccu.column_name = %s
        """,
        [table, column],
    )
    if fk_rows:
        # give a helpful message
        refs = ", ".join(f"{r['from_table']}.{r['from_column']}" for r in fk_rows[:5])
        more = "" if len(fk_rows) <= 5 else f" (+{len(fk_rows)-5} more)"
        abort(400, f"Cannot delete '{table}.{column}' because it is referenced by: {refs}{more}")
    exec_sql(db, f"ALTER TABLE {qident(table)} DROP COLUMN {qident(column)}")
    return ok_response(None)

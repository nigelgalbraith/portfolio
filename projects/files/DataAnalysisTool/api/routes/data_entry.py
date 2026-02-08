from flask import Blueprint, request, abort

from modules.validators import require_ident, qident
from modules.db import fetch_all, fetch_one, exec_sql
from modules.responses import ok_response
from modules.data_entry import (
    get_primary_key_columns,
    get_table_column_meta,
    compute_required_columns,
    build_where_clause,
    _create_record,
    _update_record,
    get_junction_selections,
    apply_junction_selections,
)
from modules.backups import backup_database


bp = Blueprint("data_entry", __name__)


@bp.get("/api/databases/<db>/tables/<table>/schema")
def table_schema_rest(db, table):
    """Return detailed schema metadata for a table."""
    db = require_ident(db, "db")
    table = require_ident(table, "table")
    pk_cols = get_primary_key_columns(db, table)
    col_rows = get_table_column_meta(db, table)
    required_on_create = sorted(compute_required_columns(col_rows))
    columns = []
    for r in col_rows:
        name = r["column_name"]
        is_identity = (r.get("is_identity") or "NO").upper() == "YES"
        is_generated = (r.get("is_generated") or "NEVER").upper() != "NEVER"
        is_pk = name in pk_cols
        editable_on_create = (not is_identity) and (not is_generated)
        editable_on_update = (not is_identity) and (not is_generated) and (not is_pk)
        columns.append(
            {
                "name": name,
                "type": r.get("data_type"),
                "isNullable": (r.get("is_nullable") or "YES").upper() == "YES",
                "hasDefault": r.get("column_default") is not None,
                "isIdentity": is_identity,
                "isGenerated": is_generated,
                "isPrimaryKey": is_pk,
                "maxLength": r.get("character_maximum_length"),
                "editableOnCreate": editable_on_create,
                "editableOnUpdate": editable_on_update,
            }
        )
    return ok_response(
        {
            "db": db,
            "table": table,
            "primaryKey": pk_cols,
            "requiredOnCreate": required_on_create,
            "columns": columns,
        }
    )


@bp.get("/api/databases/<db>/tables/<table>/primary-key")
def primary_key_rest(db, table):
    """Return primary key columns for a table."""
    db = require_ident(db, "db")
    table = require_ident(table, "table")
    return ok_response({"columns": get_primary_key_columns(db, table)})


@bp.post("/api/databases/<db>/tables/<table>/records/query")
def query_records_rest(db, table):
    """Query records with filters, sorting, and paging."""
    db = require_ident(db, "db")
    table = require_ident(table, "table")
    data = request.json or {}
    limit = int(data.get("limit") or 50)
    offset = int(data.get("offset") or 0)
    if limit < 1 or limit > 500:
        abort(400, "limit must be 1..500")
    if offset < 0:
        abort(400, "offset must be >= 0")
    filters = data.get("filters") or {}
    if not isinstance(filters, dict):
        abort(400, "filters must be an object")
    where_sql, params = build_where_clause(filters)
    pk_cols = get_primary_key_columns(db, table)
    if pk_cols:
        order_sql = " ORDER BY " + ", ".join(qident(c, "column") for c in pk_cols)
    else:
        order_sql = " ORDER BY 1"
    sql = f"SELECT * FROM {qident(table, 'table')}{where_sql}{order_sql} LIMIT %s OFFSET %s"
    rows = fetch_all(db, sql, tuple(params + [limit, offset]))
    return ok_response({"rows": rows, "limit": limit, "offset": offset})


@bp.post("/api/databases/<db>/tables/<table>/records/get")
def get_record_rest(db, table):
    """Return one record by primary key."""
    db = require_ident(db, "db")
    table = require_ident(table, "table")
    data = request.json or {}
    pk = data.get("pk") or {}
    if not isinstance(pk, dict) or not pk:
        abort(400, "pk object required")
    pk_cols = get_primary_key_columns(db, table)
    if not pk_cols:
        abort(400, "Table has no primary key; cannot fetch a single record safely.")
    missing = [c for c in pk_cols if c not in pk]
    if missing:
        abort(400, f"Missing pk columns: {', '.join(missing)}")
    where_sql, params = build_where_clause({c: pk[c] for c in pk_cols})
    sql = f"SELECT * FROM {qident(table, 'table')}{where_sql} LIMIT 1"
    row = fetch_one(db, sql, tuple(params))
    return ok_response({"row": row})


@bp.post("/api/databases/<db>/tables/<table>/records")
def create_record_rest(db, table):
    """Create a new record in a table."""
    db = require_ident(db, "db")
    backup_database(db, reason="before create_record")
    table = require_ident(table, "table")
    data = request.json or {}
    values = data.get("values")
    if values is None or not isinstance(values, dict):
        abort(400, "values object must be an object")
    pk, _required_cols = _create_record(db, table, values)
    return ok_response({"pk": pk})


@bp.patch("/api/databases/<db>/tables/<table>/records")
def update_record_rest(db, table):
    """Update an existing record in a table."""
    db = require_ident(db, "db")
    backup_database(db, reason="before update_record")
    table = require_ident(table, "table")
    data = request.json or {}
    pk = data.get("pk")
    changes = data.get("changes")
    if changes is None or not isinstance(changes, dict):
        abort(400, "changes object must be an object")
    pk_out = _update_record(db, table, pk, changes)
    return ok_response({"pk": pk_out})


@bp.post("/api/databases/<db>/tables/<table>/records/delete")
def delete_record_rest(db, table):
    """Delete a record by primary key."""
    db = require_ident(db, "db")
    backup_database(db, reason="before delete_record")
    table = require_ident(table, "table")
    data = request.json or {}
    pk = data.get("pk") or {}
    if not isinstance(pk, dict) or not pk:
        abort(400, "pk object required")
    pk_cols = get_primary_key_columns(db, table)
    if not pk_cols:
        abort(400, "Table has no primary key; cannot delete safely.")
    missing = [c for c in pk_cols if c not in pk]
    if missing:
        abort(400, f"Missing pk columns: {', '.join(missing)}")
    where_sql, params = build_where_clause({c: pk[c] for c in pk_cols})
    sql = f"DELETE FROM {qident(table,'table')}{where_sql}"
    exec_sql(db, sql, tuple(params))
    return ok_response(None)


@bp.get("/api/databases/<db>/tables/<table>/distinct/<column>")
def distinct_values_rest(db, table, column):
    """Return distinct non-null values for a column."""
    db = require_ident(db, "db")
    table = require_ident(table, "table")
    column = require_ident(column, "column")
    limit = int(request.args.get("limit") or 50)
    if limit < 1 or limit > 500:
        abort(400, "limit must be 1..500")
    sql = f"""
      SELECT DISTINCT {qident(column,'column')} AS v
      FROM {qident(table,'table')}
      WHERE {qident(column,'column')} IS NOT NULL
      ORDER BY 1
      LIMIT %s
    """
    rows = fetch_all(db, sql, (limit,))
    return ok_response([r["v"] for r in rows])


@bp.get("/api/databases/<db>/tables/<table>/lookup")
def lookup_rest(db, table):
    """Return lookup rows for dropdowns."""
    db = require_ident(db, "db")
    table = require_ident(table, "table")
    value_col = require_ident(request.args.get("value_col") or "", "column")
    label_col = request.args.get("label_col") or ""
    label_col = require_ident(label_col, "column") if label_col else value_col
    limit = int(request.args.get("limit") or 50)
    if limit < 1 or limit > 500:
        abort(400, "limit must be 1..500")
    search = (request.args.get("search") or "").strip()
    params = []
    where = ""
    if search:
        where = f" WHERE CAST({qident(label_col,'column')} AS TEXT) ILIKE %s"
        params.append(f"%{search}%")
    sql = f"""
      SELECT {qident(value_col,'column')} AS value,
             {qident(label_col,'column')} AS label
      FROM {qident(table,'table')}
      {where}
      ORDER BY 2
      LIMIT %s
    """
    params.append(limit)
    rows = fetch_all(db, sql, tuple(params))
    return ok_response(rows)


@bp.get("/api/databases/<db>/junctions/selection")
def get_junction_selection_rest(db):
    """Return selected far-side ids for a junction set."""
    db = require_ident(db, "db")
    junction_table = require_ident(request.args.get("junction_table") or "", "junction table")
    main_fk_column = require_ident(request.args.get("main_fk_column") or "", "main fk column")
    far_fk_column = require_ident(request.args.get("far_fk_column") or "", "far fk column")
    main_id = request.args.get("main_id")
    if main_id is None or str(main_id).strip() == "":
        abort(400, "main_id required")
    rows = get_junction_selections(db, junction_table, main_fk_column, main_id, far_fk_column)
    return ok_response(rows)


@bp.post("/api/databases/<db>/junctions/selection")
def apply_junction_selection_rest(db):
    """Replace junction selections with the provided far ids."""
    db = require_ident(db, "db")
    data = request.json or {}
    junction_table = require_ident(data.get("junctionTable", ""), "junction table")
    main_fk_column = require_ident(data.get("mainFkColumn", ""), "main fk column")
    far_fk_column = require_ident(data.get("farFkColumn", ""), "far fk column")
    main_id = data.get("mainId")
    if main_id is None or str(main_id).strip() == "":
        abort(400, "mainId required")
    far_ids = data.get("farIds") or []
    apply_junction_selections(db, junction_table, main_fk_column, main_id, far_fk_column, far_ids)
    return ok_response({"ok": True})

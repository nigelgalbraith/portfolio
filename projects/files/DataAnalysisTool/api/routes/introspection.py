from flask import Blueprint, request, abort

from modules.validators import require_ident
from modules.db import fetch_all
from modules.responses import ok_response
from modules.visibility import is_hidden_table
from modules.table_meta import ensure_meta_table, seed_meta_rows, fetch_table_meta, upsert_table_meta

bp = Blueprint("introspection", __name__)


@bp.get("/api/databases/<db>/schema")
def database_schema_rest(db):
    """Return tables, columns, and FK metadata for a database."""
    db = require_ident(db, "db")
    tables = fetch_all(
        db,
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        """,
    )
    # Hide internal tool tables from schema consumers.
    tables = [t for t in tables if not is_hidden_table(t["table_name"])]
    cfg = {"tables": {}, "tableMeta": {}}
    table_names: list[str] = []
    for t in tables:
        table = t["table_name"]
        table_names.append(table)
        cols = fetch_all(
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
        pk = fetch_all(
            db,
            """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid
             AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass
              AND i.indisprimary
            """,
            (table,),
        )
        cfg["tables"][table] = {
            "columns": [{"name": c["column_name"], "type": c["data_type"]} for c in cols],
            "primaryKey": [p["attname"] for p in pk],
            "foreignKeys": [],
        }
    fks = fetch_all(
        db,
        """
        SELECT
          tc.table_name,
          kcu.column_name,
          ccu.table_name AS ref_table,
          ccu.column_name AS ref_column,
          rc.delete_rule,
          rc.update_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.constraint_schema = tc.table_schema
        JOIN information_schema.referential_constraints rc
          ON rc.constraint_name = tc.constraint_name
         AND rc.constraint_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
        """,
    )
    for fk in fks:
        if fk["table_name"] not in cfg["tables"]:
            continue
        cfg["tables"][fk["table_name"]]["foreignKeys"].append(
            {
                "column": fk["column_name"],
                "refTable": fk["ref_table"],
                "refColumn": fk["ref_column"],
                "onDelete": fk["delete_rule"],
                "onUpdate": fk["update_rule"],
            }
        )
    # Tool table metadata (table roles)
    ensure_meta_table(db)
    seed_meta_rows(db, table_names)
    cfg["tableMeta"] = fetch_table_meta(db)
    return ok_response(cfg)


@bp.post("/api/databases/<db>/table-meta")
def set_table_meta_rest(db):
    """Upsert per-table metadata (role/label/junction mode)."""
    db = require_ident(db, "db")
    ensure_meta_table(db)
    data = request.json or {}
    table_name = require_ident(data.get("tableName", ""), "table name")
    table_type = (data.get("tableType", "") or "").strip()
    allowed_types = {"entity", "lookup", "junction"}
    if table_type not in allowed_types:
        abort(400, f"Invalid tableType: {table_type}")
    label_column = data.get("labelColumn", None)
    if label_column is not None and str(label_column).strip() != "":
        label_column = require_ident(str(label_column), "label column")
    else:
        label_column = None
    junction_mode = data.get("junctionMode", None)
    if junction_mode is not None and str(junction_mode).strip() != "":
        junction_mode = str(junction_mode).strip()
        if junction_mode not in {"simple", "with_data"}:
            abort(400, f"Invalid junctionMode: {junction_mode}")
    else:
        junction_mode = None
    # Ensure table exists in public schema
    exists = fetch_all(
        db,
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = %s
        LIMIT 1
        """,
        (table_name,),
    )
    if not exists:
        abort(400, f"Unknown table: {table_name}")
    upsert_table_meta(
        db,
        table_name=table_name,
        table_type=table_type,
        label_column=label_column,
        junction_mode=junction_mode,
    )
    return ok_response(
        {
            "tableName": table_name,
            "tableType": table_type,
            "labelColumn": label_column,
            "junctionMode": junction_mode,
        }
    )

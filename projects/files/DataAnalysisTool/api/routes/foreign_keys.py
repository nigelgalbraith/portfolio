from flask import Blueprint, request, abort

from modules.validators import require_ident, qident
from modules.db import fetch_all, exec_sql, pg_conn
from modules.responses import ok_response
from modules.sql_utils import safe_fk_name
from modules.backups import backup_database

bp = Blueprint("foreign_keys", __name__)


@bp.get("/api/databases/<db>/tables/<table>/foreign-keys")
def list_foreign_keys_rest(db, table):
    """Return foreign key metadata for a table."""
    db = require_ident(db, "db")
    table = require_ident(table, "table")
    rows = fetch_all(
        db,
        """
        SELECT
          tc.constraint_name,
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
         AND ccu.table_schema = tc.table_schema
        JOIN information_schema.referential_constraints rc
          ON rc.constraint_name = tc.constraint_name
        WHERE tc.table_schema = 'public'
          AND tc.table_name = %s
          AND tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.constraint_name
        """,
        (table,),
    )
    return ok_response(
        [
            {
                "name": r["constraint_name"],
                "column": r["column_name"],
                "refTable": r["ref_table"],
                "refColumn": r["ref_column"],
                "onDelete": r["delete_rule"],
                "onUpdate": r["update_rule"],
            }
            for r in rows
        ]
    )


@bp.post("/api/databases/<db>/tables/<table>/foreign-keys")
def create_foreign_key_rest(db, table):
    """Create a foreign key, optionally in auto mode."""
    db = require_ident(db, "db")
    backup_database(db, reason="before create_foreign_key")
    table = require_ident(table, "table")
    d = request.json or {}
    auto = bool(d.get("auto"))
    if auto:
        fk_col = require_ident(d.get("fkColumn", ""), "fkColumn")
        to_table = require_ident(d.get("toTable", ""), "toTable")
        to_col = require_ident(d.get("toColumn", ""), "toColumn")
        on_delete = (d.get("onDelete") or "RESTRICT").upper()
        on_update = (d.get("onUpdate") or "RESTRICT").upper()
        allowed = {"RESTRICT", "CASCADE", "SET NULL", "NO ACTION"}
        if on_delete not in allowed:
            abort(400, "Invalid onDelete")
        if on_update not in allowed:
            abort(400, "Invalid onUpdate")
        with pg_conn(db) as cn:
            with cn.cursor() as cur:
                # 1) Create FK column if missing
                cur.execute(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = %s
                      AND column_name = %s
                    """,
                    (table, fk_col),
                )
                created_col = False
                if cur.fetchone() is None:
                    cur.execute(f"ALTER TABLE {qident(table)} ADD COLUMN {qident(fk_col)} BIGINT")
                    created_col = True
                # 2) Create index if missing (Postgres does NOT auto-index FKs)
                idx_name = f"{table}_{fk_col}_idx"
                cur.execute(
                    """
                    SELECT 1
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename = %s
                      AND indexname = %s
                    """,
                    (table, idx_name),
                )
                created_idx = False
                if cur.fetchone() is None:
                    cur.execute(f"CREATE INDEX {qident(idx_name)} ON {qident(table)} ({qident(fk_col)})")
                    created_idx = True
                # 3) Add FK constraint
                fk_name = safe_fk_name(table, fk_col, to_table, to_col)
                cur.execute(
                    f"""
                    ALTER TABLE {qident(table)}
                    ADD CONSTRAINT {qident(fk_name)}
                    FOREIGN KEY ({qident(fk_col)})
                    REFERENCES {qident(to_table)} ({qident(to_col)})
                    ON DELETE {on_delete}
                    ON UPDATE {on_update}
                    """
                )
        return ok_response(
            {
                "name": safe_fk_name(table, fk_col, to_table, to_col),
                "createdColumn": created_col,
                "createdIndex": created_idx,
            }
        )
    # simple mode
    col = require_ident(d.get("fromColumn", ""), "column")
    ref_table = require_ident(d.get("toTable", ""), "refTable")
    ref_col = require_ident(d.get("toColumn", ""), "refColumn")
    fk = safe_fk_name(table, col, ref_table, ref_col)
    exec_sql(
        db,
        f"""
        ALTER TABLE {qident(table)}
        ADD CONSTRAINT {qident(fk)}
        FOREIGN KEY ({qident(col)})
        REFERENCES {qident(ref_table)} ({qident(ref_col)})
        """,
    )
    return ok_response({"name": fk})


@bp.delete("/api/databases/<db>/tables/<table>/foreign-keys/<fk_name>")
def delete_foreign_key_rest(db, table, fk_name):
    """Remove a foreign key constraint from a table."""
    db = require_ident(db, "db")
    backup_database(db, reason="before delete_foreign_key")
    table = require_ident(table, "table")
    fk_name = require_ident(fk_name, "fk name")
    exec_sql(db, f"ALTER TABLE {qident(table)} DROP CONSTRAINT {qident(fk_name)}")
    return ok_response(None)

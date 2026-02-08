import psycopg2
from flask import Blueprint, request

from modules.validators import require_ident
from modules.db import fetch_all, pg_admin_conn
from modules.responses import ok_response
from modules.visibility import is_hidden_database
from modules.visibility import is_hidden_database

bp = Blueprint("databases", __name__)


@bp.get("/api/databases")
def list_databases():
    """List non-hidden databases available to the user."""
    rows = fetch_all(
        None,
        """
        SELECT datname
        FROM pg_database
        WHERE datistemplate = false
        ORDER BY datname
        """,
    )
    return ok_response(
        [
            {"id": r["datname"], "label": r["datname"]}
            for r in rows
            if not is_hidden_database(r["datname"])
        ]
    )


@bp.post("/api/databases")
def create_database_rest():
    """Create a database unless it already exists."""
    data = request.json or {}
    db = require_ident(data.get("db", ""), "database name")
    conn = pg_admin_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{db}"')
    except psycopg2.errors.DuplicateDatabase:
        return ok_response({"db": db, "alreadyExists": True})
    finally:
        conn.close()
    return ok_response({"db": db, "alreadyExists": False})

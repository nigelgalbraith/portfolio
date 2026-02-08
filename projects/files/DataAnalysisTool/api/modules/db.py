import os

import psycopg2
import psycopg2.extras


def pg_conn(db: str | None = None):
    """Return a database connection to the target database."""
    return psycopg2.connect(
        host=os.environ.get("PG_HOST", "postgres"),
        user=os.environ.get("PG_USER", "appuser"),
        password=os.environ.get("PG_PASSWORD", "apppassword"),
        dbname=db or os.environ.get("PG_DB", "postgres"),
    )


def pg_admin_conn():
    """Return an autocommit admin connection for database creation."""
    conn = psycopg2.connect(
        host=os.environ.get("PG_HOST", "postgres"),
        user=os.environ.get("PG_USER", "appuser"),
        password=os.environ.get("PG_PASSWORD", "apppassword"),
        dbname=os.environ.get("PG_ADMIN_DB", "postgres"),
    )
    conn.set_session(autocommit=True)
    return conn


def fetch_all(db, sql, params=None):
    """Execute a query and return all rows as dicts."""
    with pg_conn(db) as cn:
        with cn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()


def fetch_one(db, sql, params=None):
    """Execute a query and return a single row as a dict."""
    with pg_conn(db) as cn:
        with cn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()


def exec_sql(db, sql, params=None):
    """Execute a statement and return a simple ok result."""
    with pg_conn(db) as cn:
        with cn.cursor() as cur:
            cur.execute(sql, params or ())
    return {"ok": True}

import psycopg2
from psycopg2 import Error as PGError
from flask import Flask
from werkzeug.exceptions import HTTPException

from modules.responses import error_response, _pg_error_details

# Blueprints
from routes.pages import bp as pages_bp
from routes.databases import bp as databases_bp
from routes.introspection import bp as introspection_bp
from routes.tables import bp as tables_bp
from routes.columns import bp as columns_bp
from routes.foreign_keys import bp as foreign_keys_bp
from routes.configs import bp as configs_bp
from routes.summary import bp as summary_bp
from routes.data_entry import bp as data_entry_bp
from routes.docs import bp as docs_bp
from routes.health import bp as health_bp
from modules.backups import run_startup_backups, should_run_startup_tasks


app = Flask(__name__)

# -----------------------------
# Error handlers
# -----------------------------
@app.errorhandler(PGError)
def handle_pg_error(e: PGError):
    """Map common Postgres errors to sensible HTTP status codes."""
    pgcode = getattr(e, "pgcode", "") or ""
    details = _pg_error_details(e)

    # Constraint violations
    if pgcode in ("23505",):  # unique_violation
        return error_response(409, "Unique constraint violation", code="UNIQUE_VIOLATION", details=details)
    if pgcode in ("23503",):  # foreign_key_violation
        return error_response(409, "Foreign key constraint violation", code="FOREIGN_KEY_VIOLATION", details=details)
    if pgcode in ("23502",):  # not_null_violation
        return error_response(400, "NOT NULL constraint violation", code="NOT_NULL_VIOLATION", details=details)
    if pgcode in ("23514",):  # check_violation
        return error_response(400, "CHECK constraint violation", code="CHECK_VIOLATION", details=details)

    if app.debug:
        return error_response(500, str(e), code="PG_ERROR", details=details)
    return error_response(500, "Database error", code="PG_ERROR", details=details)


@app.errorhandler(HTTPException)
def handle_http_error(e):
    return error_response(e.code or 500, e.description, code="HTTP_ERROR")


@app.errorhandler(Exception)
def handle_unhandled_error(e):
    if app.debug:
        return error_response(500, str(e), code="UNHANDLED_ERROR")
    return error_response(500, "Internal server error", code="UNHANDLED_ERROR")


# -----------------------------
# Register blueprints
# -----------------------------
app.register_blueprint(pages_bp)
app.register_blueprint(databases_bp)
app.register_blueprint(introspection_bp)
app.register_blueprint(tables_bp)
app.register_blueprint(columns_bp)
app.register_blueprint(foreign_keys_bp)
app.register_blueprint(configs_bp)
app.register_blueprint(summary_bp)
app.register_blueprint(data_entry_bp)
app.register_blueprint(docs_bp)
app.register_blueprint(health_bp)


# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    if should_run_startup_tasks(app.debug):
        try:
            print(run_startup_backups(reason="startup"))
        except Exception as e:
            print(f"[startup_backup] failed: {e}")

    app.run(host="0.0.0.0", port=5000, debug=True)

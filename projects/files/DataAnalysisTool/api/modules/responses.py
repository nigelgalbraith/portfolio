from psycopg2 import Error as PGError
from flask import jsonify


def ok_response(data=None):
    """Return a standard ok response envelope."""
    return jsonify({"ok": True, "data": data})


def error_response(status: int, message: str, code: str | None = None, details: dict | None = None):
    """Return a consistent error envelope."""
    err = {"message": message, "status": status}
    if code:
        err["code"] = code
    if details:
        err["details"] = details
    return jsonify({"ok": False, "error": err}), status


def _pg_error_details(e: PGError) -> dict:
    """Extract safe, user-facing details from a psycopg2 error."""
    details: dict = {}
    pgcode = getattr(e, "pgcode", None)
    if pgcode:
        details["pgcode"] = pgcode
    diag = getattr(e, "diag", None)
    if diag:
        constraint = getattr(diag, "constraint_name", None)
        if constraint:
            details["constraint"] = constraint
        # message_detail can reveal involved keys; useful for debugging but still safe enough for local tools.
        msg_detail = getattr(diag, "message_detail", None)
        if msg_detail:
            details["detail"] = msg_detail
    return details

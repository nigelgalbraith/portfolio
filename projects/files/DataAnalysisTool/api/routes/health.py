from flask import Blueprint
from modules.responses import ok_response

bp = Blueprint("health", __name__)

@bp.get("/api/health")
def api_health():
    """Basic liveness check for the API."""
    return ok_response({"ok": True})

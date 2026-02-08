"""Summary routes.

Routes are intentionally thin; business/query logic lives in modules.
"""

from flask import Blueprint, request, abort

from modules.validators import require_ident
from modules.responses import ok_response
from modules.summary_service import run_summary as run_summary_service, SummaryConfigError


bp = Blueprint("summary", __name__)


@bp.post("/api/summary/run")
def run_summary():
    """Run a summary query based on a strict v2 config."""
    data = request.json or {}
    cfg = data.get("config") or {}
    db = require_ident(cfg.get("db", ""), "db")
    main = require_ident(cfg.get("mainTable", ""), "table")
    summary_fields = cfg.get("summaryFields") or []
    detail_fields = cfg.get("detailFields") or []
    try:
        result = run_summary_service(db, main, summary_fields, detail_fields)
    except SummaryConfigError as e:
        abort(400, str(e))
    return ok_response(result)

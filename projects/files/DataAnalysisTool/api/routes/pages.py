from flask import Blueprint

from modules.responses import ok_response

bp = Blueprint("pages", __name__)

PAGES = [
    {"id": "database", "label": "Database Settings", "module": "/src/pages/databaseSettings.js"},
    {"id": "relationships", "label": "Relationships", "module": "/src/pages/relationshipsPage.js"},
    {"id": "sumSet", "label": "Summary Settings", "module": "/src/pages/summarySettings.js"},
    {"id": "summary", "label": "Summary Table", "module": "/src/pages/summaryPage.js"},
    {"id": "dataEntry", "label": "Data Entry", "module": "/src/pages/dataEntryPage.js"},
]


@bp.get("/api/pages")
def api_pages():
    """Return the list of page definitions for the UI."""
    return ok_response(PAGES)

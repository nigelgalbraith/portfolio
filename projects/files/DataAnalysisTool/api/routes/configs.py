from flask import Blueprint, request

from modules.validators import require_config_id
from modules.responses import ok_response
from modules.config_store import (
    list_config_ids, load_config, create_config, save_config, delete_config, config_exists
)

bp = Blueprint("configs", __name__)


@bp.get("/api/configs")
def list_configs_rest():
    """List available config ids for selection."""
    return ok_response([{"id": cid, "label": cid} for cid in list_config_ids()])


@bp.get("/api/configs/<config_id>")
def get_config_rest(config_id):
    """Return the stored config for a given id."""
    data = load_config(config_id)
    return ok_response({"id": require_config_id(config_id), "data": data})


@bp.post("/api/configs")
def create_config_rest():
    """Create a new config entry."""
    d = request.json or {}
    cid = require_config_id(d.get("id", ""), "config id")
    data = d.get("data", None)
    create_config(cid, data)
    return ok_response(None)


@bp.put("/api/configs/<config_id>")
def save_config_rest(config_id):
    """Overwrite an existing config entry."""
    cid = require_config_id(config_id, "config id")
    d = request.json or {}
    data = d.get("data", None)
    save_config(cid, data)
    return ok_response(None)


@bp.delete("/api/configs/<config_id>")
def delete_config_rest(config_id):
    """Delete a config by id if it exists."""
    existed = delete_config(config_id)
    return ok_response({"alreadyMissing": not existed}) if not existed else ok_response(None)


@bp.route("/api/configs/<config_id>", methods=["HEAD"])
def config_exists_rest(config_id):
    """Return 200 if a config exists, else 404."""
    cid = require_config_id(config_id, "config id")
    return ("", 200) if config_exists(cid) else ("", 404)

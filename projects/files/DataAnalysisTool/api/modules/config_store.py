import os
import json

from flask import abort

from modules.validators import require_config_id, config_id_is_valid

CONFIG_DIR = os.getenv('CONFIG_DIR', '/app/storage/configs')


def ensure_config_dir():
    """Ensure the config storage directory exists."""
    os.makedirs(CONFIG_DIR, exist_ok=True)



def config_path(config_id: str) -> str:
    """Return the absolute JSON file path for a validated config id."""
    ensure_config_dir()
    cid = require_config_id(config_id)
    return os.path.join(CONFIG_DIR, f"{cid}.json")



def list_config_ids() -> list[str]:
    """List valid config ids present in the config directory."""
    ensure_config_dir()
    ids: list[str] = []
    for name in sorted(os.listdir(CONFIG_DIR)):
        if not name.endswith('.json'):
            continue
        cid = name[:-5]
        if config_id_is_valid(cid):
            ids.append(cid)
    return ids



def load_config(config_id: str) -> dict:
    """Load and return a config JSON file by id or raise 404 if missing."""
    path = config_path(config_id)
    if not os.path.exists(path):
        abort(404, 'Config not found')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)



def create_config(config_id: str, data) -> None:
    """Create a new config JSON file; fail if missing data or id exists."""
    cid = require_config_id(config_id)
    if data is None:
        abort(400, 'Missing config data')
    path = config_path(cid)
    if os.path.exists(path):
        abort(400, 'Config already exists')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)



def save_config(config_id: str, data) -> None:
    """Save (overwrite) a config JSON file for the given id."""
    cid = require_config_id(config_id)
    if data is None:
        abort(400, 'Missing config data')
    ensure_config_dir()
    path = config_path(cid)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)



def delete_config(config_id: str) -> bool:
    """Delete a config JSON file by id and return whether it was removed."""
    path = config_path(config_id)
    if not os.path.exists(path):
        return False
    os.remove(path)
    return True



def config_exists(config_id: str) -> bool:
    """Return True if a config JSON file exists for the given id."""
    cid = require_config_id(config_id)
    return os.path.exists(config_path(cid))

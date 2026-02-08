import re
from flask import abort

# NOTE:
# - Identifiers used in SQL object names are kept strict to prevent injection.
# - Config IDs are stored as filenames: allow '-' too.
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CONFIG_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def require_ident(value: str, what: str = "identifier") -> str:
    """Validate a strict SQL identifier (db/table/column/name)."""
    if not isinstance(value, str):
        abort(400, f"Invalid {what}: {value}")
    value = value.strip()
    if not _IDENT_RE.match(value):
        abort(400, f"Invalid {what}: {value}")
    return value


def require_config_id(v, label: str = "config id") -> str:
    """Validate a config id used as a filename (no extension)."""
    if not isinstance(v, str):
        abort(400, f"Invalid {label}: {v}")
    cid = v.strip()
    # Forbid extension (configs are stored as <id>.json)
    if cid.endswith(".json"):
        abort(400, f"Invalid {label}: {v}")
    # Enforce the same rule everywhere
    if not _CONFIG_RE.match(cid):
        abort(400, f"Invalid {label}: {v}")
    return cid


def qident(value: str, what: str = "identifier") -> str:
    """Quote a validated identifier for safe SQL interpolation."""
    return f'"{require_ident(value, what)}"'


def config_id_is_valid(cid: str) -> bool:
    """Check config id validity without raising HTTP errors."""
    return isinstance(cid, str) and bool(_CONFIG_RE.match(cid.strip()))


def ident_re() -> re.Pattern:
    """Expose identifier regex (rarely needed)."""
    return _IDENT_RE


def config_re() -> re.Pattern:
    """Expose config id regex (rarely needed)."""
    return _CONFIG_RE

import os
import time
import subprocess
from pathlib import Path
from datetime import datetime

import psycopg2

# -----------------------------
# Config
# -----------------------------
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/app/storage/backups"))
KEEP_LAST = int(os.getenv("BACKUP_KEEP_LAST", "10"))

PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", "appuser")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")
PG_ADMIN_DB = os.getenv("PG_ADMIN_DB", "postgres")

STARTUP_BACKUP_DAYS = int(os.getenv("STARTUP_BACKUP_DAYS", "1"))

# -----------------------------
# Private helpers
# -----------------------------
def _rotate(db_dir: Path) -> None:
    backups = sorted(db_dir.glob("*.sql"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[KEEP_LAST:]:
        old.unlink(missing_ok=True)


def _list_databases() -> list[str]:
    """List non-template DBs."""
    cn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_ADMIN_DB,
    )
    try:
        with cn.cursor() as cur:
            cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
            return [r[0] for r in cur.fetchall()]
    finally:
        cn.close()


def _newest_backup_mtime(db_name: str) -> float | None:
    """Return newest backup mtime for db_name, or None if none exist."""
    db_dir = BACKUP_DIR / "postgres" / db_name
    if not db_dir.exists():
        return None

    backups = sorted(db_dir.glob("*.sql"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        return None

    return backups[0].stat().st_mtime


# -----------------------------
# Public API
# -----------------------------
def should_run_startup_tasks(debug: bool) -> bool:
    """
    Avoid running twice under Flask debug reloader.
    Run only in the reloader child process, or always when not debugging.
    """
    if not debug:
        return True
    return os.environ.get("WERKZEUG_RUN_MAIN") == "true"


def backup_database(db_name: str, reason: str = "schema-change") -> dict:
    """Create a rotated SQL dump for db_name using pg_dump."""
    db_dir = BACKUP_DIR / "postgres" / db_name
    db_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = db_dir / f"db_{ts}.sql"

    env = os.environ.copy()
    if PG_PASSWORD:
        env["PGPASSWORD"] = PG_PASSWORD

    cmd = [
        "pg_dump",
        "-h", PG_HOST,
        "-p", str(PG_PORT),
        "-U", PG_USER,
        db_name,
    ]

    try:
        with out_file.open("w", encoding="utf-8") as f:
            subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                env=env,
                check=True,
            )
    except subprocess.CalledProcessError as e:
        out_file.unlink(missing_ok=True)
        raise RuntimeError(f"pg_dump failed: {e.stderr.decode(errors='ignore')}") from e

    _rotate(db_dir)

    return {"ok": True, "db": db_name, "reason": reason, "file": str(out_file)}


def run_startup_backups(reason: str = "startup") -> dict:
    """
    Backup DBs at startup only if newest backup is older than STARTUP_BACKUP_DAYS,
    or if there are no backups yet.
    """
    dbs = _list_databases()

    now = time.time()
    max_age_sec = STARTUP_BACKUP_DAYS * 86400

    results = {
        "ok": True,
        "days": STARTUP_BACKUP_DAYS,
        "backed_up": [],
        "skipped": [],
        "errors": [],
    }

    for db in dbs:
        newest = _newest_backup_mtime(db)
        needs = (newest is None) or ((now - newest) > max_age_sec)

        if not needs:
            results["skipped"].append(db)
            continue

        try:
            backup_database(db, reason=f"{reason}:{db}")
            results["backed_up"].append(db)
        except Exception as e:
            results["ok"] = False
            results["errors"].append({"db": db, "error": str(e)})

    return results


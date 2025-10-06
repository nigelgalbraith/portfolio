# modules/state_machine_utils.py
from __future__ import annotations
import argparse
import importlib
from typing import Any, Dict


def load_constants_from_module(module_path: str, required: list[str]):
    """Import constants module and return a namespace-like object."""
    mod = importlib.import_module(module_path)
    consts = {name: getattr(mod, name) for name in dir(mod) if name.isupper()}
    missing = [n for n in required if n not in consts]
    if missing:
        raise SystemExit(
            f"[FATAL] Constants module '{module_path}' is missing: {', '.join(missing)}"
        )
    return type("Constants", (), consts)()


def parse_args_early() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--constants", help="Python module path for constants (e.g. constants.DebConstants)")
    return p.parse_known_args()[0]


def resolve_arg(spec: Any, job: str, meta: Dict[str, Any], ctx: Dict[str, Any]) -> Any:
    """Resolve a pipeline arg: callable → ctx → meta (supports dotted) → 'job' → literal."""
    if callable(spec):
        return spec(job, meta, ctx)
    if isinstance(spec, str):
        if spec in ctx:
            return ctx[spec]
        key = spec.split(".", 1)[-1]
        if key in meta:
            return meta[key]
        if spec == "job":
            return job
    return spec


def check_when(cond: Any, job: str, meta: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    """Evaluate a step's 'when' condition (callable or arg spec or truthy literal)."""
    if cond is None:
        return True
    if callable(cond):
        return bool(cond(job, meta, ctx))
    return bool(resolve_arg(cond, job, meta, ctx))


def status_candidates(job_status: Dict[str, bool], want: Optional[bool]) -> List[str]:
    """Return job names filtered by desired status without changing original order."""
    if want is None:
        return list(job_status.keys())
    if want is True:
        return [j for j, ok in job_status.items() if ok]
    return [j for j, ok in job_status.items() if not ok]


def parse_args(consts: Any) -> argparse.Namespace:
    """Parse CLI flags for non-interactive operation."""
    p = argparse.ArgumentParser(description="Installer state machine")
    p.add_argument("--yes", "-y", action="store_true", help="Auto-confirm prompts (non-interactive).")

    action_choices = [k for k in consts.ACTIONS.keys() if k != "_meta"]
    if "Cancel" in action_choices:
        action_choices = [c for c in action_choices if c != "Cancel"] + ["Cancel"]

    p.add_argument("--action", choices=action_choices,
                   help="Action to perform non-interactively.")
    p.add_argument("--targets", help="Comma-separated list of job names to operate on (used with --action).")
    p.add_argument("--status", action="store_true", help="Status-only: show installed/uninstalled summary and exit.")
    p.add_argument("--plan-only", action="store_true", help="Print the execution plan and exit without making changes.")
    p.add_argument("--constants", default="constants.DebConstants",
                   help="Python module path for constants (e.g. constants.DebConstants)")
    return p.parse_args()

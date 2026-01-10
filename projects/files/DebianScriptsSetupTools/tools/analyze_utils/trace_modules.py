#!/usr/bin/env python3
"""
Runtime tracer: record which functions in modules.* were ACTUALLY called.

Batch mode (default):
- Accepts 1 or more program paths.
- Prints ONE summary for the whole batch (not per program).

Usage:
  python3 tools/trace_modules.py --module modules.firewall_utils <program1.py> <program2.py> ...
  python3 tools/trace_modules.py <program1.py> <program2.py> ...

Forward args to EACH program (same args for every program):
  python3 tools/trace_modules.py --module modules.firewall_utils <program.py> -- <args...>
"""

from __future__ import annotations

import runpy
import sys
import ast
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Set, Tuple


# =========================
# CONSTANTS
# =========================

TRACE_PREFIX = "modules."

# =========================
# ARG PARSING
# =========================

def split_at_double_dash(items: List[str]) -> Tuple[List[str], List[str]]:
    """Split items into (before '--', after '--')."""
    if "--" not in items:
        return items, []
    i = items.index("--")
    return items[:i], items[i + 1 :]


def parse_args(argv: List[str]) -> Tuple[str | None, Path | None, List[Path], List[str]]:
    """
    Parse:
      [--modules-dir /path/to/modules] [--module modules.x]
      <program1.py> [program2.py ...] [-- args...]
    """
    if len(argv) < 2:
        raise ValueError(
            "Usage: python3 tools/trace_modules.py [--modules-dir <dir>] [--module modules.x] <program1.py> [program2.py ...] [-- args...]"
        )

    rest = argv[1:]
    module_filter: str | None = None
    modules_dir: Path | None = None

    if rest and rest[0] == "--modules-dir":
        if len(rest) < 2:
            raise ValueError("Missing value after --modules-dir")
        modules_dir = Path(rest[1]).resolve()
        rest = rest[2:]

    if rest and rest[0] == "--module":
        if len(rest) < 2:
            raise ValueError("Missing value after --module")
        module_filter = rest[1]
        rest = rest[2:]

    prog_parts, prog_args = split_at_double_dash(rest)

    if not prog_parts:
        raise ValueError("No program paths provided.")

    programs = [Path(p).resolve() for p in prog_parts]
    return module_filter, modules_dir, programs, prog_args


# =========================
# TRACING
# =========================

def find_module_file(modules_dir: Path, module_name: str) -> Path | None:
    """
    Resolve modules.<name> to <modules_dir>/<name>.py without importing.
    """
    if not module_name.startswith("modules."):
        return None
    stem = module_name.split(".", 1)[1]
    path = modules_dir / f"{stem}.py"
    return path if path.exists() else None


def make_profiler(calls: DefaultDict[str, Set[str]], trace_prefix: str):
    """Return a profiler function that records function calls under trace_prefix."""
    def _profiler(frame, event, arg):
        if event != "call":
            return _profiler

        mod = frame.f_globals.get("__name__", "") or ""
        if not mod.startswith(trace_prefix):
            return _profiler

        fn = frame.f_code.co_name
        calls[mod].add(fn)
        return _profiler

    return _profiler


def run_one_program(program: Path, prog_args: List[str], trace_prefix: str) -> Tuple[int, Dict[str, Set[str]], str]:
    """
    Run one program under profiler.
    Returns (exit_code, calls_dict[module -> set(funcs)], error_summary).
    error_summary is "" when exit_code == 0.
    """
    calls: DefaultDict[str, Set[str]] = defaultdict(set)
    profiler = make_profiler(calls, trace_prefix)

    sys.argv = [str(program)] + prog_args

    try:
        sys.setprofile(profiler)
        runpy.run_path(str(program), run_name="__main__")
        exit_code = 0
        err = ""
    except SystemExit as e:
        code = e.code
        exit_code = int(code) if isinstance(code, int) else 0 if code is None else 1
        err = f"SystemExit({e.code})" if exit_code != 0 else ""
    except Exception as e:
        exit_code = 1
        err = f"{type(e).__name__}: {e}"
    finally:
        sys.setprofile(None)

    return exit_code, dict(calls), err


# =========================
# SUMMARY HELPERS
# =========================

def get_top_level_functions_from_file(py_file: Path) -> Set[str]:
    """Return top-level function names from a Python file."""
    try:
        text = py_file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text, filename=str(py_file))
    except Exception:
        return set()

    funcs: Set[str] = set()
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.FunctionDef):
            funcs.add(node.name)
    return funcs


def filter_calls(calls: Dict[str, Set[str]], module_filter: str | None) -> Dict[str, Set[str]]:
    """Return calls filtered to module_filter if provided."""
    if not module_filter:
        return calls
    return {module_filter: calls.get(module_filter, set())}


def count_funcs(calls: Dict[str, Set[str]]) -> int:
    """Count total unique function names across modules."""
    return sum(len(v) for v in calls.values())


def merge_calls(into: DefaultDict[str, Set[str]], calls: Dict[str, Set[str]]) -> None:
    """Merge calls into accumulator."""
    for mod, funcs in calls.items():
        into[mod].update(funcs)


def print_batch_summary(
    module_filter: str | None,
    modules_dir: Path | None,
    attempted: int,
    ok: int,
    failed: int,
    missing: int,
    merged_calls: Dict[str, Set[str]],
    succeeded_programs: List[str],
    failed_programs: List[str],
    missing_programs: List[str],
) -> None:
    """Print ONE summary for the whole batch run."""

    filtered_calls = (
        {module_filter: merged_calls.get(module_filter, set())}
        if module_filter
        else merged_calls
    )

    total_called = sum(len(v) for v in filtered_calls.values())

    print("\n=== TRACE SUMMARY ===")
    print(f"Module filter: {module_filter or '(none)'}")
    print(f"Programs attempted: {attempted}")
    print(f"Succeeded: {ok}")
    print(f"Failed: {failed}")
    print(f"Missing/not found: {missing}")
    print(f"Functions called (unique): {total_called}")
    # Inconclusive cases
    if module_filter and ok == 0:
        print("\nResult: TRACE INCONCLUSIVE (0 programs succeeded).")
        print("Nothing executed, so no module functions could be observed.")

    elif module_filter and total_called == 0:
        print("\nResult: No runtime calls detected for this module in these runs.")
        print("Possible reasons:")
        print(" - The module was imported but none of its functions were called, or")
        print(" - The relevant code paths did not execute.")

    if module_filter and (ok == 0 or total_called == 0):
        print("\nNote about menu-driven entrypoints:")
        print(" - If the entrypoint uses an interactive menu (e.g., DebianLoader.py),")
        print("   the module may not be exercised unless you actually select the menu")
        print("   options that call it.")
        print(" - This can produce a false 'not called' result.")

    # Function-level reporting
    if module_filter and modules_dir:
        module_file = None

        if module_filter.startswith("modules."):
            stem = module_filter.split(".", 1)[1]
            candidate = modules_dir / f"{stem}.py"
            if candidate.exists():
                module_file = candidate

        if module_file:
            try:
                tree = ast.parse(
                    module_file.read_text(encoding="utf-8", errors="replace"),
                    filename=str(module_file),
                )
                defined_funcs = {
                    node.name
                    for node in tree.body
                    if isinstance(node, ast.FunctionDef)
                }
            except Exception:
                defined_funcs = set()

            called_funcs = filtered_calls.get(module_filter, set())
            not_called = defined_funcs - called_funcs

            print(f"\nModule file: {module_file}")
            print(f"Functions defined: {len(defined_funcs)}")
            print(f"Functions observed called: {len(called_funcs)}")

            if ok == 0:
                print("Functions NOT called: (unknown — nothing executed)")
            elif not_called:
                print("\nFunctions NOT called in these runs:")
                for fn in sorted(not_called):
                    print(f"  - {fn}")
            else:
                print("\nAll functions in this module were called in these runs.")

        else:
            print("\n[WARNING] Could not resolve module file to compare defined vs called.")

    elif module_filter and not modules_dir:
        print("\n[INFO] No --modules-dir provided; skipping defined-vs-called comparison.")

    # Program outcome reporting
    if succeeded_programs:
        print("\nPrograms that ran successfully:")
        for name in succeeded_programs:
            print(f"  - {name}")

    if failed_programs:
        print("\nPrograms that failed to run:")
        for name in failed_programs:
            print(f"  - {name}")

    if missing_programs:
        print("\nPrograms missing/not found:")
        for name in missing_programs:
            print(f"  - {name}")


# =========================
# MAIN
# =========================

def main() -> int:
    try:
        module_filter, modules_dir, programs, prog_args = parse_args(sys.argv)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return 2

    attempted = 0
    ok = 0
    failed = 0
    missing = 0

    succeeded_programs: List[str] = []
    failed_programs: List[str] = []
    missing_programs: List[str] = []
    failed_reasons: Dict[str, str] = {}

    merged: DefaultDict[str, Set[str]] = defaultdict(set)

    for program in programs:
        attempted += 1

        if not program.exists() or not program.is_file():
            missing += 1
            missing_programs.append(program.name)
            continue

        exit_code, calls, err = run_one_program(program, prog_args, TRACE_PREFIX)

        if exit_code == 0:
            ok += 1
            succeeded_programs.append(program.name)
            merge_calls(merged, calls)
        else:
            failed += 1
            failed_programs.append(program.name)
            if err:
                failed_reasons[program.name] = err

    print_batch_summary(
        module_filter=module_filter,
        modules_dir=modules_dir,
        attempted=attempted,
        ok=ok,
        failed=failed,
        missing=missing,
        merged_calls=dict(merged),
        succeeded_programs=succeeded_programs,
        failed_programs=failed_programs,
        missing_programs=missing_programs,
    )

    return 0 if failed == 0 and missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

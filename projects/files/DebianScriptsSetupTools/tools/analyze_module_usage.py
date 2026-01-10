#!/usr/bin/env python3
"""
AST-based module function usage report (interactive module selection).

Phase 1 (this tool):
- Inventory top-level functions in modules/*.py
- Find direct references in PROGRAM files (file + line numbers)
- Mark indirect usage via intra-module call graph (helpers called by used funcs)
- Print unused functions

Phase 2 (optional):
- If unused functions are found and you answer trace = y,
  this tool runs trace_modules.py ONCE against ENTRYPOINT files only.
- trace_modules.py owns all trace output and summaries.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# =========================
# CONSTANTS
# =========================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODULE_DIRS = [
    PROJECT_ROOT / "modules",
]

# Phase 1 (AST scan) program sources:
PROGRAM_DIRS = [
    PROJECT_ROOT / "constants",
]
PROGRAM_FILES = [
    PROJECT_ROOT / "DebianLoader.py",
]

# Phase 2 (runtime trace) entrypoints ONLY:
ENTRYPOINT_FILES = [
    PROJECT_ROOT / "DebianLoader.py",
    # Add more real runnable entrypoints here later
]

TRACE_TOOL = PROJECT_ROOT / "tools" / "analyze_utils" / "trace_modules.py"

SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "tools",
}
SKIP_FILES = {"__init__.py"}


# =========================
# HELPERS
# =========================

def should_skip_path(p: Path, skip_dirs: Set[str], skip_files: Set[str]) -> bool:
    """Return True if path should be skipped."""
    if p.name.startswith("."):
        return True
    if p.name in skip_files:
        return True
    if any(x in p.parts for x in skip_dirs):
        return True
    return False


def safe_read(path: Path) -> str:
    """Read file content safely."""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_ast(path: Path) -> Optional[ast.AST]:
    """Parse file to AST; return None if syntax error."""
    try:
        return ast.parse(safe_read(path), filename=str(path))
    except SyntaxError:
        return None


def relpath_str(path: Path, root: Path) -> str:
    """Return a nice relative path string."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def list_py_files_recursive(dir_path: Path, skip_dirs: Set[str], skip_files: Set[str]) -> List[Path]:
    """List *.py files under dir_path recursively."""
    if not dir_path.exists():
        return []
    out: List[Path] = []
    for p in dir_path.rglob("*.py"):
        if should_skip_path(p, skip_dirs, skip_files):
            continue
        out.append(p)
    return sorted(out)


def list_py_files_flat(dir_path: Path, skip_dirs: Set[str], skip_files: Set[str]) -> List[Path]:
    """List *.py files directly inside dir_path."""
    if not dir_path.exists():
        return []
    out: List[Path] = []
    for p in sorted(dir_path.glob("*.py")):
        if should_skip_path(p, skip_dirs, skip_files):
            continue
        out.append(p)
    return out


def dedupe_paths_keep_order(paths: List[Path]) -> List[Path]:
    """De-dupe a list while preserving order."""
    seen: Set[Path] = set()
    out: List[Path] = []
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


def module_qualname(module_dir: Path, module_file: Path) -> str:
    """Return modules.foo for modules/foo.py."""
    return f"{module_dir.name}.{module_file.stem}"


def get_top_level_function_nodes(tree: ast.AST) -> Dict[str, ast.FunctionDef]:
    """Return top-level function nodes by name."""
    out: Dict[str, ast.FunctionDef] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            out[node.name] = node
    return out


def called_simple_names(func_node: ast.FunctionDef) -> Set[str]:
    """Return names called like helper() in this function."""
    out: Set[str] = set()
    for n in ast.walk(func_node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            out.add(n.func.id)
    return out


def build_intra_module_call_graph(func_nodes: Dict[str, ast.FunctionDef]) -> Dict[str, Set[str]]:
    """Map func -> set(other top-level funcs called via simple name calls)."""
    names = set(func_nodes.keys())
    graph: Dict[str, Set[str]] = {fn: set() for fn in names}
    for fn, node in func_nodes.items():
        graph[fn] = {c for c in called_simple_names(node) if c in names and c != fn}
    return graph


def closure(graph: Dict[str, Set[str]], roots: Set[str]) -> Set[str]:
    """Transitive closure from roots."""
    seen: Set[str] = set()
    stack: List[str] = list(roots)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for nxt in graph.get(cur, set()):
            if nxt not in seen:
                stack.append(nxt)
    return seen


def dotted_name(node: ast.AST) -> Optional[str]:
    """Return dotted name for Name/Attribute chain or None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)
        if left is None:
            return None
        return f"{left}.{node.attr}"
    return None


def add_ref(
    usage: Dict[str, Dict[str, Dict[str, Set[int]]]],
    mod: str,
    fn: str,
    file_key: str,
    lineno: int,
) -> None:
    """Record a direct reference."""
    usage.setdefault(mod, {}).setdefault(fn, {}).setdefault(file_key, set()).add(lineno)


def ensure_usage_slots(
    usage: Dict[str, Dict[str, Dict[str, Set[int]]]],
    module_funcs: Dict[str, Set[str]],
) -> None:
    """Ensure all module/function keys exist."""
    for mod, funcs in module_funcs.items():
        usage.setdefault(mod, {})
        for fn in funcs:
            usage[mod].setdefault(fn, {})


def build_program_list(
    program_dirs: List[Path],
    program_files: List[Path],
    skip_dirs: Set[str],
    skip_files: Set[str],
) -> List[Path]:
    """Build de-duped program list from PROGRAM_DIRS + PROGRAM_FILES."""
    out: List[Path] = []

    for d in program_dirs:
        out.extend(list_py_files_recursive(d, skip_dirs, skip_files))

    for f in program_files:
        if f.exists() and f.is_file() and f.suffix == ".py":
            if not should_skip_path(f, skip_dirs, skip_files):
                out.append(f)

    return dedupe_paths_keep_order(out)


def build_entrypoint_list(entrypoints: List[Path]) -> List[Path]:
    """Build de-duped list of valid entrypoints (runtime trace)."""
    out: List[Path] = []
    for p in entrypoints:
        if p.exists() and p.is_file() and p.suffix == ".py":
            out.append(p)
    return dedupe_paths_keep_order(out)


def pick_from_menu(title: str, items: List[str]) -> List[int] | None:
    """Menu picker: returns indexes, ALL, or CANCEL."""
    print(f"\n{title}")
    for i, label in enumerate(items, start=1):
        print(f"  {i}) {label}")
    print(f"  {len(items) + 1}) ALL")
    print(f"  {len(items) + 2}) CANCEL")
    print()

    raw = input("Enter a number: ").strip()
    if not raw.isdigit():
        print("[WARNING] Invalid input.")
        return []

    choice = int(raw)
    if 1 <= choice <= len(items):
        return [choice - 1]
    if choice == len(items) + 1:
        return list(range(len(items)))
    if choice == len(items) + 2:
        return None

    print("[WARNING] Invalid choice.")
    return []


def ask_yes_no(prompt: str) -> bool:
    """Prompt yes/no; return True for yes."""
    return input(prompt).strip().lower() == "y"


def run_python_tool(tool_path: Path, args: List[str]) -> int:
    """Run a python tool script with args and show its output."""
    if not tool_path.exists():
        print(f"[ERROR] Tool not found: {tool_path}")
        return 2

    cmd = [sys.executable, str(tool_path)] + args
    result = subprocess.run(cmd, text=True, capture_output=True)

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    return result.returncode


def print_program_list(title: str, programs: List[Path], root: Path) -> None:
    """Print a readable list of programs being processed."""
    print(title)
    for p in programs:
        print(f"  - {relpath_str(p, root)}")
    print()


def scan_import_context(
    tree: ast.AST,
    known_modules: Set[str],
) -> Tuple[Dict[str, str], Dict[str, Tuple[str, str]], Set[str]]:
    """Return module alias map, imported func alias map, and star-imported modules."""
    module_alias: Dict[str, str] = {}
    imported_func_alias: Dict[str, Tuple[str, str]] = {}
    star_imports: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mod = a.name
                if mod in known_modules:
                    alias = a.asname or mod.split(".")[-1]
                    module_alias[alias] = mod

        elif isinstance(node, ast.ImportFrom):
            mod = node.module
            if not mod or mod not in known_modules:
                continue
            for a in node.names:
                if a.name == "*":
                    star_imports.add(mod)
                    continue
                local_name = a.asname or a.name
                imported_func_alias[local_name] = (mod, a.name)

    return module_alias, imported_func_alias, star_imports


def record_direct_usage(
    tree: ast.AST,
    file_key: str,
    module_funcs: Dict[str, Set[str]],
    module_alias: Dict[str, str],
    imported_func_alias: Dict[str, Tuple[str, str]],
    star_imports: Set[str],
    direct_usage: Dict[str, Dict[str, Dict[str, Set[int]]]],
    direct_roots: Dict[str, Set[str]],
) -> None:
    """Record direct usage refs into direct_usage and direct_roots."""
    # star import: mark all functions as "root-used" at the import line
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in star_imports:
            lineno = getattr(node, "lineno", 0) or 0
            mod = node.module
            for fn in module_funcs.get(mod, set()):
                add_ref(direct_usage, mod, fn, file_key, lineno)
                direct_roots[mod].add(fn)

    # direct imported functions used as Name nodes
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in imported_func_alias:
            mod, fn = imported_func_alias[node.id]
            if fn in module_funcs.get(mod, set()):
                add_ref(direct_usage, mod, fn, file_key, getattr(node, "lineno", 0) or 0)
                direct_roots[mod].add(fn)

    # attribute usage: modules.x.fn OR alias.fn
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        full = dotted_name(node)
        if not full:
            continue

        parts = full.split(".")

        # modules.x.fn
        if len(parts) >= 3 and parts[0] == "modules":
            mod = ".".join(parts[:2])
            fn = parts[2]
            if mod in module_funcs and fn in module_funcs.get(mod, set()):
                add_ref(direct_usage, mod, fn, file_key, getattr(node, "lineno", 0) or 0)
                direct_roots[mod].add(fn)
            continue

        # alias.fn
        if len(parts) == 2:
            alias, fn = parts
            if alias in module_alias:
                mod = module_alias[alias]
                if fn in module_funcs.get(mod, set()):
                    add_ref(direct_usage, mod, fn, file_key, getattr(node, "lineno", 0) or 0)
                    direct_roots[mod].add(fn)


def print_report_for_modules(
    selected_modules: List[str],
    module_funcs: Dict[str, Set[str]],
    direct_usage: Dict[str, Dict[str, Dict[str, Set[int]]]],
    indirect_only: Dict[str, Set[str]],
) -> int:
    """Print report and return unused count for selection."""
    unused_count = 0
    print("\n=== AST FUNCTION USAGE REPORT ===\n")

    for mod in selected_modules:
        funcs = sorted(module_funcs.get(mod, set()))

        print(mod)
        print("-" * len(mod))

        for fn in funcs:
            refs = direct_usage.get(mod, {}).get(fn, {})
            is_indirect = fn in indirect_only.get(mod, set())

            if refs:
                parts: List[str] = []
                for file_key in sorted(refs.keys()):
                    lines = sorted(refs[file_key])
                    parts.append(f"{file_key}:{','.join(map(str, lines))}")
                print(f"  {fn}: " + "; ".join(parts))
            elif is_indirect:
                print(f"  {fn}: (indirect)")
            else:
                unused_count += 1
                print(f"  {fn}: (unused)")
        print()

    return unused_count


def print_end_summary(scanned_programs: int, scanned_modules: int) -> None:
    """Print final scan summary (at end)."""
    print(f"Scanned programs: {scanned_programs}")
    print(f"Modules scanned:  {scanned_modules}")


# =========================
# MAIN
# =========================

def main() -> int:
    # Phase 1: Build program list ONCE from PROGRAM_DIRS + PROGRAM_FILES
    program_files = build_program_list(PROGRAM_DIRS, PROGRAM_FILES, SKIP_DIRS, SKIP_FILES)

    if not program_files:
        print("[ERROR] No program files found to scan.")
        return 2

    # Phase 2: Build entrypoints list ONCE from ENTRYPOINT_FILES
    entrypoints = build_entrypoint_list(ENTRYPOINT_FILES)

    # Module inventory + call graphs
    module_funcs: Dict[str, Set[str]] = {}
    module_graph: Dict[str, Dict[str, Set[str]]] = {}

    for mdir in MODULE_DIRS:
        for py in list_py_files_flat(mdir, SKIP_DIRS, SKIP_FILES):
            mod = module_qualname(mdir, py)
            tree = parse_ast(py)
            if tree is None:
                continue

            func_nodes = get_top_level_function_nodes(tree)
            module_funcs[mod] = set(func_nodes.keys())
            module_graph[mod] = build_intra_module_call_graph(func_nodes)

    if not module_funcs:
        print("[ERROR] No module functions found.")
        return 2

    known_modules = set(module_funcs.keys())
    known_modules_sorted = sorted(known_modules)

    # Direct usage + roots
    direct_usage: Dict[str, Dict[str, Dict[str, Set[int]]]] = {}
    ensure_usage_slots(direct_usage, module_funcs)
    direct_roots: Dict[str, Set[str]] = {m: set() for m in module_funcs.keys()}

    for src in program_files:
        tree = parse_ast(src)
        if tree is None:
            continue

        file_key = relpath_str(src, PROJECT_ROOT)
        module_alias, imported_func_alias, star_imports = scan_import_context(tree, known_modules)

        record_direct_usage(
            tree=tree,
            file_key=file_key,
            module_funcs=module_funcs,
            module_alias=module_alias,
            imported_func_alias=imported_func_alias,
            star_imports=star_imports,
            direct_usage=direct_usage,
            direct_roots=direct_roots,
        )

    # Indirect usage (within module)
    indirect_only: Dict[str, Set[str]] = {m: set() for m in module_funcs.keys()}
    for mod in module_funcs.keys():
        roots = direct_roots.get(mod, set())
        graph = module_graph.get(mod, {})
        if not roots or not graph:
            continue
        used_all = closure(graph, roots)
        for fn in used_all:
            if fn not in roots:
                indirect_only[mod].add(fn)

    # Menu loop
    while True:
        idxs = pick_from_menu("Select a module to report on:", known_modules_sorted)

        if idxs is None:
            print("\nCancelled.\n")
            break

        if not idxs:
            continue

        selected_modules = [known_modules_sorted[i] for i in idxs]
        unused_count = print_report_for_modules(selected_modules, module_funcs, direct_usage, indirect_only)

        # If unused found and single module selected, offer trace y/n
        if unused_count > 0 and len(selected_modules) == 1:
            mod = selected_modules[0]
            if ask_yes_no(f"Unused functions found in {mod}. Run trace on this module? (y/n): "):
                if not TRACE_TOOL.exists():
                    print(f"[ERROR] Trace tool not found: {TRACE_TOOL}")
                    continue

                if not entrypoints:
                    print("[WARNING] No valid ENTRYPOINT_FILES found.")
                    print("Add runnable scripts to ENTRYPOINT_FILES (not constants modules).")
                    continue

                print(f"\n[INFO] Running trace on ENTRYPOINTS ({len(entrypoints)}) for: {mod}\n")
                print_program_list("[INFO] Entrypoints to trace:", entrypoints, PROJECT_ROOT)

                args = ["--modules-dir", str(MODULE_DIRS[0]), "--module", mod] + [str(p) for p in entrypoints]
                run_python_tool(TRACE_TOOL, args)

    print_end_summary(scanned_programs=len(program_files), scanned_modules=len(module_funcs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

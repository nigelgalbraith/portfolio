#!/usr/bin/env python3
"""ERD PlantUML generator (class-based, with column anchors).

- Reads ONE shared style JSON (colors, skinparams, “hide …”, prelude/footer).
- Reads EVERY ERD JSON in SCHEMAS_DIR (entities, relationships, layout).
- Emits a .puml next to each ERD JSON.
- Optionally renders to PNG/SVG into OUTPUT_DIR.
- No auto-FKs, no magic: JSON controls everything.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterable
import json, os, shutil, subprocess, sys


# =========
# CONSTANTS
# =========
SCHEMAS_DIR = Path("../diagrams/ERDs")           # where your *.json ERD files live
STYLE_PATH  = Path("../diagrams/ERDConfig.json") # single shared style JSON
OUTPUT_DIR  = Path("../projects/images/main/original")  # rendered images go here
RENDER      = True                                # False → only write .puml files
RENDER_FMT  = "png"                               # png | svg
# =========================


# ---------- IO helpers ----------
def load_json(p: Path) -> Dict[str, Any]:
    """Load a JSON file into a dict."""
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def write_text(p: Path, text: str) -> None:
    """Write text to a file."""
    p.write_text(text, encoding="utf-8")

def plantuml_cmd() -> Optional[List[str]]:
    """Return the PlantUML executable command list, or None if not found."""
    if shutil.which("plantuml"):
        return ["plantuml"]
    jar = os.environ.get("PLANTUML_JAR")
    if jar and Path(jar).exists():
        return ["java", "-jar", jar]
    return None

def render(puml_path: Path, fmt: str) -> Optional[Path]:
    """Render a .puml file using PlantUML; return the output path if it exists."""
    cmd = plantuml_cmd()
    if not cmd:
        return None
    subprocess.run(cmd + [f"-t{fmt}", str(puml_path)],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    out = puml_path.with_suffix(f".{fmt}")
    return out if out.exists() else None


# ---------- PUML builders ----------
def skinparam_lines(skinparams: Dict[str, Any]) -> Iterable[str]:
    """Yield PlantUML skinparam lines from a dict (handles booleans)."""
    for k, v in skinparams.items():
        if isinstance(v, bool):
            val = "true" if v else "false"
        else:
            val = v
        yield f"skinparam {k} {val}"

def class_block(e: Dict[str, Any]) -> str:
    """Return a PlantUML 'class' block string for an entity with fields."""
    name = e["name"]
    display = e.get("display", name)
    cols = "\n".join(f"  {c['name']}" for c in e.get("columns", []))
    return f'class "{display}" as {name} {{\n{cols}\n}}'

def relationship_text(r: Dict[str, Any], cmap: Dict[str, str]) -> str:
    """Return a PlantUML relationship/operator line from a relationship dict."""
    op = cmap.get(r.get("cardinality", "1..N"), "--")
    direction = r.get("direction")
    if direction in {"up", "down", "left", "right"}:
        op = op.replace("--", f"-{direction}-")
    if "label" in r:
        return f'{r["from"]} {op} {r["to"]} : "{r["label"]}"'
    return f'{r["from"]} {op} {r["to"]}'

def _add_title_and_caption(schema: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    if schema.get("title"):
        out.append(f'title {schema["title"]}')
    if schema.get("notes"):
        out.append(f'caption {schema["notes"]}')
    return out

def _add_prelude(style: Dict[str, Any]) -> List[str]:
    return list(style.get("prelude", []))

def _add_skinparams(style: Dict[str, Any]) -> List[str]:
    sp = style.get("skinparams", {})
    return list(skinparam_lines(sp)) if sp else []

def _add_hide(style: Dict[str, Any]) -> List[str]:
    return [f"hide {h}" for h in style.get("hide", [])]

def _add_entities(schema: Dict[str, Any], style: Dict[str, Any]) -> List[str]:
    out = ["' --- entities ---"]
    for e in schema.get("entities", []):
        out.append(class_block(e))
        out.append("")
    return out

def _add_relationships(schema: Dict[str, Any], style: Dict[str, Any]) -> List[str]:
    out = ["' --- relationships ---"]
    cmap = style.get("relationship_styles", {}).get("cardinality_map", {}) or {
        "1..1": "--", "1..N": "--", "0..N": "--", "0..1": "--", "N..N": "--", "N..1": "--"
    }
    for r in schema.get("relationships", []):
        out.append(relationship_text(r, cmap))
    return out

def _add_layout(schema: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    layout = schema.get("layout", {})
    for group in layout.get("same_row", []):
        if isinstance(group, list) and len(group) >= 2:
            for a, b in zip(group, group[1:]):
                out.append(f"{a} -[hidden]right- {b}")
    rank = layout.get("rank", {})
    for t in rank.get("top", []):
        for b in rank.get("bottom", []):
            out.append(f"{t} -[hidden]down- {b}")
    return out

def _add_footer(style: Dict[str, Any]) -> List[str]:
    return list(style.get("footer", []))

def build_puml(schema: Dict[str, Any], style: Dict[str, Any]) -> str:
    lines: List[str] = ["@startuml"]
    lines.extend(_add_title_and_caption(schema))
    lines.extend(_add_prelude(style))
    lines.extend(_add_skinparams(style))
    lines.extend(_add_hide(style))
    lines.extend(_add_entities(schema, style))
    lines.extend(_add_relationships(schema, style))
    lines.extend(_add_layout(schema))
    lines.extend(_add_footer(style))
    lines.append("@enduml")
    return "\n".join(lines)


# ---------- main ----------
def main() -> None:
    if not OUTPUT_DIR.exists():
        print(f"Error: OUTPUT_DIR does not exist: {OUTPUT_DIR}")
        sys.exit(1)
    if not SCHEMAS_DIR.exists():
        print(f"Error: SCHEMAS_DIR does not exist: {SCHEMAS_DIR}")
        sys.exit(1)

    style = load_json(STYLE_PATH)
    schema_files = sorted(SCHEMAS_DIR.glob("*.json"))
    if not schema_files:
        print(f"No schema JSON files found in {SCHEMAS_DIR}")
        return

    for sf in schema_files:
        schema = load_json(sf)
        puml = build_puml(schema, style)

        out_puml = sf.with_suffix(".puml")
        write_text(out_puml, puml)
        print(f"Wrote {out_puml}")

        if RENDER:
            out_img = render(out_puml, RENDER_FMT)
            if out_img:
                final = OUTPUT_DIR / out_img.name
                if final.exists():
                    final.unlink()
                shutil.move(str(out_img), str(final))
                print(f"Rendered {final}")
            else:
                print("PlantUML not found.")

if __name__ == "__main__":
    main()

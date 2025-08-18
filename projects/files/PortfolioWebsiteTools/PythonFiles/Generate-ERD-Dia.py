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
RENDER_FMT  = "png"                               # png | svg
# =========================


# ---------- IO helpers ----------
def load_json(p: Path) -> Dict[str, Any]:
    """Load and parse a JSON file into a Python dict."""
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def write_text(p: Path, text: str) -> None:
    """Write a string of text to a UTF-8 file, overwriting if it exists."""
    p.write_text(text, encoding="utf-8")


def plantuml_cmd() -> Optional[List[str]]:
    """Return the PlantUML command list (binary or JAR call), or None if unavailable."""
    if shutil.which("plantuml"):
        return ["plantuml"]
    jar = os.environ.get("PLANTUML_JAR")
    if jar and Path(jar).exists():
        return ["java", "-jar", jar]
    return None


def render(puml_path: Path, fmt: str) -> Optional[Path]:
    """Render a .puml file to the requested format using PlantUML; return output path if successful."""
    cmd = plantuml_cmd()
    if not cmd:
        return None
    subprocess.run(cmd + [f"-t{fmt}", str(puml_path)],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    out = puml_path.with_suffix(f".{fmt}")
    return out if out.exists() else None


# ---------- PUML builders ----------
def skinparam_lines(skinparams: Dict[str, Any]) -> Iterable[str]:
    """Yield PlantUML skinparam lines from a dictionary (booleans handled as true/false)."""
    for k, v in skinparams.items():
        val = "true" if isinstance(v, bool) and v else "false" if isinstance(v, bool) else v
        yield f"skinparam {k} {val}"


def class_block(e: Dict[str, Any]) -> str:
    """Return a PlantUML class block string for an entity and its columns."""
    name = e["name"]
    display = e.get("display", name)
    cols = "\n".join(f"  {c['name']}" for c in e.get("columns", []))
    return f'class "{display}" as {name} {{\n{cols}\n}}'


def relationship_text(r: Dict[str, Any], cmap: Dict[str, str]) -> str:
    """Return a PlantUML relationship line from a relationship dict and cardinality map."""
    op = cmap.get(r.get("cardinality", "1..N"), "--")
    direction = r.get("direction")
    if direction in {"up", "down", "left", "right"}:
        op = op.replace("--", f"-{direction}-")
    if "label" in r:
        return f'{r["from"]} {op} {r["to"]} : "{r["label"]}"'
    return f'{r["from"]} {op} {r["to"]}'


def _add_title_and_caption(schema: Dict[str, Any]) -> List[str]:
    """Generate PlantUML title and caption lines from schema metadata."""
    out: List[str] = []
    if schema.get("title"):
        out.append(f'title {schema["title"]}')
    if schema.get("notes"):
        out.append(f'caption {schema["notes"]}')
    return out


def _add_prelude(style: Dict[str, Any]) -> List[str]:
    """Return any prelude lines defined in the style config."""
    return list(style.get("prelude", []))


def _add_skinparams(style: Dict[str, Any]) -> List[str]:
    """Return skinparam lines from the style config."""
    sp = style.get("skinparams", {})
    return list(skinparam_lines(sp)) if sp else []


def _add_hide(style: Dict[str, Any]) -> List[str]:
    """Return hide directives from the style config."""
    return [f"hide {h}" for h in style.get("hide", [])]


def _add_entities(schema: Dict[str, Any], style: Dict[str, Any]) -> List[str]:
    """Build PlantUML class blocks for all entities in the schema."""
    out = ["' --- entities ---"]
    for e in schema.get("entities", []):
        out.append(class_block(e))
        out.append("")
    return out


def _add_relationships(schema: Dict[str, Any], style: Dict[str, Any]) -> List[str]:
    """Build PlantUML relationship lines for all relationships in the schema."""
    out = ["' --- relationships ---"]
    cmap = style.get("relationship_styles", {}).get("cardinality_map", {}) or {
        "1..1": "--", "1..N": "--", "0..N": "--", "0..1": "--", "N..N": "--", "N..1": "--"
    }
    for r in schema.get("relationships", []):
        out.append(relationship_text(r, cmap))
    return out


def _add_layout(schema: Dict[str, Any]) -> List[str]:
    """Add hidden connectors to influence entity layout (same row, top/bottom rank)."""
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
    """Return footer lines from the style config."""
    return list(style.get("footer", []))


def build_puml(schema: Dict[str, Any], style: Dict[str, Any]) -> str:
    """Assemble the complete PlantUML text for a schema using a given style."""
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
    """Main entrypoint: load style and schema JSONs, generate PUML files, and optionally render images."""
    
    # --- Validate required directories ---
    if not OUTPUT_DIR.exists():
        print(f"Error: OUTPUT_DIR does not exist: {OUTPUT_DIR}")
        sys.exit(1)
    if not SCHEMAS_DIR.exists():
        print(f"Error: SCHEMAS_DIR does not exist: {SCHEMAS_DIR}")
        sys.exit(1)

    # --- Load global style configuration (colors, skinparams, prelude/footer) ---
    style = load_json(STYLE_PATH)

    # --- Collect all schema JSON files from the schemas directory ---
    schema_files = sorted(SCHEMAS_DIR.glob("*.json"))
    if not schema_files:
        print(f"No schema JSON files found in {SCHEMAS_DIR}")
        return

    # --- Process each schema file ---
    for sf in schema_files:
        # Load schema definition (entities, relationships, layout)
        schema = load_json(sf)

        # Build PlantUML text from schema + style
        puml = build_puml(schema, style)

        # Write .puml file next to the JSON schema
        out_puml = sf.with_suffix(".puml")
        write_text(out_puml, puml)
        print(f"Wrote {out_puml}")

        # Render the PUML file into PNG/SVG using PlantUML
        out_img = render(out_puml, RENDER_FMT)
        if out_img:
            # Move rendered image into OUTPUT_DIR
            final = OUTPUT_DIR / out_img.name
            if final.exists():
                final.unlink()  # overwrite if needed
                shutil.move(str(out_img), str(final))
                print(f"Rendered {final}")
            else:
                print("PlantUML not found.")

if __name__ == "__main__":
    main()

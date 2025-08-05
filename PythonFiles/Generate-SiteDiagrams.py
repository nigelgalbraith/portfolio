# ======================================
# PYTHON PROGRAM FOR GENERATING SITE MAPS
# ======================================

# =======
# IMPORTS
# =======
import json
import subprocess
import sys
import shutil
from pathlib import Path

# =========
# CONSTANTS
# =========
SITEMAP_DIR = Path("../diagrams/siteMaps")
OUTPUT_DIR = Path("../projects/images/main/original")
CONFIG_FILE = "../diagrams/siteMermaidConfig.json"
MMDC_COMMAND = str(shutil.which("mmdc") or "mmdc")

# Constants for Mermaid rendering
MERMAID_STYLE_KEYS = [
    ("style", "key_styles"),
    ("classDef", "key_classes"),
    ("class", "key_class_map")
]

# ======================
# FILE + COMMAND HELPERS
# ======================
def load_json(filepath):
    """Load a JSON file and return its contents."""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Reading JSON file: {e}")
        sys.exit(1)

def write_mermaid_file(lines, filepath):
    """Write the final Mermaid syntax to a .mmd file."""
    try:
        with open(filepath, "w") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print(f"[ERROR] Failed to write Mermaid file: {e}")
        sys.exit(1)

def check_command(cmd, description=None):
    """Ensure a system command is available on the PATH."""
    if description:
        print(f"[INFO] Checking for {description} ({cmd})...")
    path = shutil.which(cmd)
    if path is None:
        print(f"[ERROR] Required system command '{cmd}' not found.")
        sys.exit(1)
    print(f"[OK] Found '{cmd}' at: {path}")

# =====================
# MERMAID BUILD HELPERS
# =====================
def write_subgraph(mermaid_lines, label, title, items):
    """Append a subgraph block with its node definitions."""
    mermaid_lines.append(f"  subgraph {label} [{title}]")
    for name, file in items.items():
        mermaid_lines.append(f"    {name}[{file}]")
    mermaid_lines.append("  end\n")

def write_link(mermaid_lines, source, target):
    """Write a single directional link (arrow) line."""
    mermaid_lines.append(f"  {source} --> {target}")

def write_mermaid_def(mermaid_lines, kind, key, value):
    """Write a single Mermaid style/class/classDef line."""
    mermaid_lines.append(f"  {kind} {key} {value}")

# =========
# RENDERING
# =========
def render_mermaid_files(mmd_file, svg_file, png_file, mmdc_cmd, config_path=None):
    """Render Mermaid .mmd file to SVG and high-res PNG using Mermaid CLI."""
    base_cmd = [mmdc_cmd, "-i", str(mmd_file)]
    if config_path:
        base_cmd.extend(["-c", config_path])

    try:
        subprocess.run(base_cmd + ["-o", str(svg_file)], check=True)
        print(f"[SUCCESS] SVG saved to: {svg_file}")
        
        subprocess.run(base_cmd + ["-o", str(png_file), "--scale", "4"], check=True)
        print(f"[SUCCESS] PNG saved to: {png_file}")

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to render Mermaid diagram: {e}")
        sys.exit(1)

# =====
# MAIN
# =====
def main():
    """Main routine to generate and render all Mermaid diagrams."""
    print("[INFO] If rendering fails, try running this script from a terminal.")
    print("Example: python3 generate_site_maps.py\n")

    check_command("node", "Node.js")
    check_command("npm", "Node Package Manager")
    check_command(MMDC_COMMAND, "Mermaid CLI")

    for json_file in sorted(SITEMAP_DIR.glob("*.json")):
        name = json_file.stem
        print(f"\n[INFO] Processing: {name}")

        site_data = load_json(json_file)
        meta = site_data.get("meta", {})

        # Validate required meta keys
        if "key_main" not in meta or "key_links" not in meta:
            print(f"[WARNING] Skipping {json_file.name}: Missing required meta keys.")
            continue

        mermaid_lines = ["graph TD\n"]

        # Build subgraphs (up to 3)
        for key_level in ("key_main", "key_second", "key_third", "key_fourth"):
            if key_level in meta:
                node_key = meta[key_level]
                if node_key in site_data:
                    label = meta.get(key_level.replace("key_", "") + "_label", node_key)
                    title = meta.get(key_level.replace("key_", "") + "_title", label)
                    write_subgraph(mermaid_lines, label, title, site_data[node_key])

        # Add links
        for source, target in site_data.get(meta["key_links"], []):
            write_link(mermaid_lines, source, target)

        # Apply styles and classes
        for kind, meta_key in MERMAID_STYLE_KEYS:
            data_key = meta.get(meta_key)
            if data_key and data_key in site_data:
                for k, v in site_data[data_key].items():
                    write_mermaid_def(mermaid_lines, kind, k, v)

        # Derive output paths
        mmd_file = json_file.with_suffix(".mmd")
        svg_file = json_file.with_suffix(".svg")
        png_file = OUTPUT_DIR / (json_file.stem + ".png")

        write_mermaid_file(mermaid_lines, mmd_file)
        render_mermaid_files(mmd_file, svg_file, png_file, MMDC_COMMAND, config_path=CONFIG_FILE)

if __name__ == "__main__":
    main()

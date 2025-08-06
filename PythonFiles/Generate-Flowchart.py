# ==============================
# PYTHON FLOWCHART CREATION TOOL
# ==============================

# =======
# IMPORTS
# =======
import json
import sys
import os
import shutil
import textwrap
from graphviz import Digraph

# =========
# CONSTANTS
# =========

# Folder paths and required command
FLOWCHART_DIR = "../diagrams/flowCharts"
CONFIG_PATH = "../diagrams/FlowConfig.json"
OUTPUT_DIR = "../projects/images/main/original"
CHECK_CMD = "dot"
CHECK_DES = "Graphviz binary"

# ================
# HELPER FUNCTIONS
# ================

def check_command(cmd, description=None):
    """Check if a command is available in the system PATH and the graphviz module is installed."""
    if description:
        print(f"[INFO] Checking for {description} ({cmd})...")
    try:
        __import__("graphviz")
    except ImportError:
        print("[ERROR] Missing Python module: graphviz. Install with 'pip install graphviz'")
        sys.exit(1)
    if shutil.which(cmd) is None:
        print(f"[ERROR] Required system command '{cmd}' not found.")
        sys.exit(1)
    print(f"[OK] Command '{cmd}' found.")

def load_json(path):
    """Load and return JSON content from a file path."""
    print(f"[INFO] Loading JSON: {path}")
    with open(path, "r") as f:
        return json.load(f)

def shape_for(type_, shape_map):
    """Return the shape for a given node type, defaulting to 'box'."""
    return shape_map.get(type_, "box")

def wrap_label(text, width):
    """Wrap long label text to improve readability in the diagram."""
    return "\n".join(textwrap.wrap(text, width))

def apply_class_styles(dot, class_definitions, class_map, node_style):
    """
    Apply class-specific styles to nodes, if defined.
    Merges default node style with any class-defined styles.
    """
    for node_id, class_name in class_map.items():
        if class_name in class_definitions:
            style = class_definitions[class_name]
            # Convert style string to dictionary
            style_dict = dict(pair.split(":") for pair in style.split(","))
            # Merge with default styles and apply to node
            dot.node(node_id, _attributes={**node_style, **style_dict})

# ===================
# DIAGRAM PREPARATION
# ===================

def prepare_diagram(name, json_path, config_path):
    """
    Load the diagram definition and config, then initialize the Graphviz Digraph.
    Returns:
    - the diagram object,
    - the raw node/connection/class data,
    - and all relevant config values.
    """
    print(f"\n[INFO] Generating flowchart: {name}")
    data = load_json(json_path)
    config = load_json(config_path)

    # Load styling/layout options from config
    defaults = config.get("defaults", {})
    node_style = config.get("node_defaults", {})
    edge_style = config.get("edge_defaults", {})
    shape_map = config.get("shape_map", {})
    label_wrap_width = int(defaults.get("labelwrap", 28))

    # Set up base diagram structure
    dot = Digraph(name=name, format="png", engine="dot")
    dot.attr(rankdir=defaults.get("rankdir", "LR"))
    dot.attr(nodesep=defaults.get("nodesep", "0.5"))
    dot.attr(ranksep=defaults.get("ranksep", "0.5"))
    dot.attr(margin=defaults.get("margin", "0.2"))
    dot.attr(arrowsize=defaults.get("arrowsize", "0.6"))
    dot.attr('graph',
             pad=defaults.get("pad", "0.2"),
             dpi=defaults.get("dpi", "96"),
             splines=defaults.get("splines", "true"))
    dot.attr('node', shape='box', **node_style)

    return dot, data, config, node_style, edge_style, label_wrap_width, shape_map

def add_edge_to_dot(dot, conn, edge_style):
    """
    Add an edge (connection) between two nodes, with optional label and styling.
    Handles special styling for 'yes'/'no' labels.
    """
    src, dst = conn[0], conn[1]
    label = conn[2] if len(conn) > 2 else ""

    # Extract base edge styling
    edge_args = {
        k: str(v) for k, v in edge_style.items()
        if not k.startswith("penwidth_") and not k.startswith("fontsize_")
    }

    if label:
        # Apply thicker lines for yes/no decision labels
        penwidth = edge_style.get("penwidth_yesno", edge_style.get("penwidth", "1")) \
            if label.strip().lower() in ("yes", "no") else edge_style.get("penwidth", "1")
        edge_args.update({
            "xlabel": label,
            "fontsize": edge_style.get("fontsize", "10"),
            "penwidth": penwidth
        })
    else:
        # Style for regular unlabeled connections
        edge_args.update({
            "fontsize": edge_style.get("fontsize_alt", "8"),
            "penwidth": edge_style.get("penwidth_alt", "0.8")
        })

    dot.edge(src, dst, **edge_args)

# =====
# MAIN
# =====

def main():
    """
    Main routine: check requirements, load each diagram JSON from folder,
    and generate flowchart PNGs using base filenames.
    """
    check_command(CHECK_CMD, CHECK_DES)

    for filename in os.listdir(FLOWCHART_DIR):
        if not filename.endswith("Flow.json"):
            continue

        # Derive paths and flow name
        json_path = os.path.join(FLOWCHART_DIR, filename)
        name = filename.removesuffix("Flow.json")
        output_png = os.path.join(OUTPUT_DIR, f"{name}Flow.png")

        # Load and prepare diagram
        dot, data, config, node_style, edge_style, label_wrap_width, shape_map = prepare_diagram(
            name, json_path, CONFIG_PATH
        )

        # Load class styles from config and allow per-diagram override
        global_classes = config.get("classes", {})
        local_classes = data.get("classes", {})
        classes = {**global_classes, **local_classes}
        
        # Load flowchart data
        nodes = data.get("nodes", {})
        connections = data.get("connections", [])
        class_map = data.get("class_map", {})

        # Add all nodes with shape and wrapped labels
        for node_id, props in nodes.items():
            label = wrap_label(props.get("label", node_id), width=label_wrap_width)
            shape = shape_for(props.get("shape", "box"), shape_map)
            dot.node(node_id, label=label, shape=shape, **node_style)

        # Add flowchart edges
        for conn in connections:
            add_edge_to_dot(dot, conn, edge_style)

        # Apply class-based node styles
        apply_class_styles(dot, classes, class_map, node_style)

        # Export PNG to file path (strip .png from render path)
        dot.render(filename=output_png.removesuffix(".png"), cleanup=True)
        print(f"[SUCCESS] {filename} → {output_png}")

if __name__ == "__main__":
    main()

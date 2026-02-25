#===================================================
# PYTHON PROGRAM TO CREATE RESPONSIVE WEBSITE IMAGES
#===================================================

#========
# IMPORTS
#========
import os
import sys
from PIL import Image, ImageOps

#==========
# CONSTANTS
#==========

# Image config
IMAGE_PROFILES = {
    "main": {
        "input_dir": "../images/main/original",
        "output_base": "../images/main/optimized",
        "quality": 90,
        "sizes": {
            "desktop": {"standard": 1280, "zoom": 1920},
            "laptop":  {"standard": 1024, "zoom": 1366},
            "mobile":  {"standard": 480,  "zoom": 768}
        }
    },
    "projects": {
        "input_dir": "../projects/images/main/original",
        "output_base": "../projects/images/main/optimized",
        "quality": 90,
        "sizes": {
            "desktop": {"standard": 1280, "zoom": 1920},
            "laptop":  {"standard": 1024, "zoom": 1366},
            "mobile":  {"standard": 480,  "zoom": 768}
        }
    }
}

ASSET_SETS = {
    "thumbs": {
        "main": {
            "input_dir": "../images/thumbs/original",
            "output_dir": "../images/thumbs/optimized",
            "width": 400,
            "quality": 85
        },
        "projects": {
            "input_dir": "../projects/images/thumbs/original",
            "output_dir": "../projects/images/thumbs/optimized",
            "width": 400,
            "quality": 85
        }
    },
    "icons": {
        "main": {
            "input_dir": "../images/icons/original",
            "output_dir": "../images/icons/optimized",
            "width": 100,
            "quality": 85
        }
    }
}

FAVICON_CONFIG = {
    "input": "../images/icons/original/monitor.png",
    "output_dir": "../images/icons/optimized",
    "sizes": [16, 32, 48, 180],  
    "ico_sizes": [16, 32, 48]
}

REQUIRED_PACKAGES = ["PIL"] 
VALID_EXTS = ('.jpg', '.jpeg', '.png')

#=================
# HELPER FUNCTIONS
#=================
def check_package(package_name):
    """Check if a package is installed, else print error and exit."""
    try:
        __import__(package_name)
    except ImportError:
        print(f"Package '{package_name}' not installed.")
        sys.exit(1)

def dir_has_images(path, valid_exts):
    """Return True if the directory exists and has at least one valid image."""
    if not os.path.isdir(path):
        return False
    return any(
        f and not f.startswith('.') and f.lower().endswith(valid_exts)
        for f in os.listdir(path)
    )

def gather_input_dirs(image_profiles, asset_sets):
    """Collect all input dirs from the provided profiles and asset sets."""
    inputs = set()
    for cfg in image_profiles.values():
        inputs.add(cfg["input_dir"])
    for asset_group in asset_sets.values():
        for cfg in asset_group.values():
            inputs.add(cfg["input_dir"])
    return sorted(inputs)

#=================
# IMAGE PROCESSING
#=================
def build_resize_tasks(input_dir, output_dir, target_width, valid_exts):
    """Generate tasks for resizing images in one folder to a target width."""
    if not os.path.isdir(input_dir):
        return []
    tasks = []
    for filename in os.listdir(input_dir):
        if not filename or filename.startswith('.') or not filename.lower().endswith(valid_exts):
            continue
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        tasks.append((input_path, output_path, target_width))
    return tasks

def process_assets(input_dir, output_dir, target_width, quality, valid_exts):
    """Build resize tasks for asset images (thumbs/icons)."""
    tasks = []
    if not os.path.isdir(input_dir):
        return tasks
    for filename in os.listdir(input_dir):
        if not filename or filename.startswith('.') or not filename.lower().endswith(valid_exts):
            continue
        tasks.append((
            os.path.join(input_dir, filename),
            os.path.join(output_dir, filename),
            target_width,
            quality
        ))
    return tasks


def resize_image(input_path, output_path, target_width, quality):
    """Resize and save an image at target width and quality."""
    try:
        with Image.open(input_path) as img:
            img = ImageOps.exif_transpose(img)
            orig_width, orig_height = img.size
            if orig_width == 0:
                print(f"Skipping {input_path}: width is 0")
                return
            scale = target_width / orig_width
            target_height = int(orig_height * scale)
            img_resized = img.resize((target_width, target_height), Image.LANCZOS)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            ext = os.path.splitext(output_path)[1].lower()
            save_kwargs = {"optimize": True}
            if ext in (".jpg", ".jpeg"):
                save_kwargs["quality"] = quality
            img_resized.save(output_path, **save_kwargs)
            print(f"Saved: {output_path}")
    except Exception as e:
        print(f"Error processing {input_path}: {e}")


def generate_favicon_png(input_path, output_path, size):
    """Generate a single square favicon PNG at the given size."""
    with Image.open(input_path) as img:
        img = img.convert("RGBA")
        resized = img.resize((size, size), Image.LANCZOS)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        resized.save(output_path, optimize=True)
        print(f"Saved: {output_path}")


def generate_favicon_ico(input_path, output_path, sizes):
    """Generate a multi-size favicon.ico file."""
    with Image.open(input_path) as img:
        img = img.convert("RGBA")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, format="ICO", sizes=[(s, s) for s in sizes])
        print(f"Saved: {output_path}")        

#=====
# MAIN
#=====
def main():
    """Run all setup, processing, and resizing tasks."""
    for package in REQUIRED_PACKAGES:
        check_package(package)
    # Gather all candidate input dirs
    input_dirs = gather_input_dirs(IMAGE_PROFILES, ASSET_SETS)
    existing_inputs = [d for d in input_dirs if os.path.isdir(d)]
    if not existing_inputs:
        print("[ERROR] No input directories found. Nothing to process.")
        sys.exit(1)
    # Require at least one image present anywhere
    favicon_exists = os.path.isfile(FAVICON_CONFIG["input"])
    if not any(dir_has_images(d, VALID_EXTS) for d in existing_inputs) and not favicon_exists:
        print("[ERROR] No images found in any existing input directory. Exiting.")
        sys.exit(1)
    # --- Responsive images (no pre-creation of outputs) ---
    for label, config in IMAGE_PROFILES.items():
        in_dir = config["input_dir"]
        if not os.path.isdir(in_dir):
            print(f"[WARNING] Skipping profile '{label}': input dir not found -> {in_dir}")
            continue
        print(f"========= Processing profile: {label} =========")
        for device in ["desktop", "laptop", "mobile"]:
            versions = config["sizes"].get(device, {})
            for version_type, width in versions.items():
                output_dir = os.path.join(config["output_base"], device, version_type)
                print(f"Profile: {label} → {device} → {version_type} @ {width}px")
                tasks = build_resize_tasks(in_dir, output_dir, width, VALID_EXTS)
                if not tasks:
                    print("No images found.")
                else:
                    for task in tasks:
                        resize_image(*task, config["quality"])
            print()
    # --- Assets (thumbs/icons) ---
    for asset_type, sets in ASSET_SETS.items():
        for label, cfg in sets.items():
            in_dir = cfg["input_dir"]
            if not os.path.isdir(in_dir):
                print(f"[WARNING] Skipping {asset_type} for '{label}': input dir not found -> {in_dir}")
                continue
            print(f"========= Processing {asset_type} for: {label} =========")
            tasks = process_assets(in_dir, cfg["output_dir"], cfg["width"], cfg["quality"], VALID_EXTS)
            if not tasks:
                print("No images found.")
            else:
                for task in tasks:
                    resize_image(*task)
            print()
    # --- Favicons ---
    favicon_input = FAVICON_CONFIG["input"]
    favicon_output_dir = FAVICON_CONFIG["output_dir"]
    if os.path.isfile(favicon_input):
        print("========= Processing favicons =========")
        # PNG sizes
        for size in FAVICON_CONFIG["sizes"]:
            output_path = os.path.join(
                favicon_output_dir,
                f"favicon-{size}x{size}.png"
            )
            generate_favicon_png(favicon_input, output_path, size)
        # ICO
        ico_path = os.path.join(favicon_output_dir, "favicon.ico")
        generate_favicon_ico(
            favicon_input,
            ico_path,
            FAVICON_CONFIG["ico_sizes"]
        )
        print()
    else:
        print(f"[WARNING] Skipping favicons: source not found -> {favicon_input}")
    print("Done. Responsive images and asset images generated.")

if __name__ == "__main__":
    main()

# HomeGallery MCP Server for Image Processing
"""
Provides tools for image analysis directly to AI agents via MCP protocol.

Tools:
- analyze_image(path) — Return image properties
- compute_hash(path) — Return perceptual hash
- extract_features(path) — Return feature vector
- generate_thumbnail(path, size) — Generate and cache thumbnail
"""

import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("homegallery.mcp.image")

DATA_DIR = os.environ.get("DATA_DIR", "data")
PHOTO_DIR = os.environ.get("PHOTO_DIR", "data")
THUMBNAIL_DIR = os.environ.get("THUMBNAIL_DIR", "data/thumbnails")
EMBEDDINGS_DIR = os.path.join(DATA_DIR, "embeddings")


def _init_dirs():
    os.makedirs(THUMBNAIL_DIR, exist_ok=True)
    os.makedirs(EMBEDDINGS_DIR, exist_ok=True)


_init_dirs()


def analyze_image(path: str) -> dict:
    """Return image properties: dimensions, format, file size, EXIF summary."""
    try:
        from PIL import Image
        import os

        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}

        stat = os.stat(path)
        with Image.open(path) as img:
            exif = img.getexif()
            exif_summary = {}
            for tag_id, value in exif.items():
                tag_name = str(exif.get_tag_name(tag_id) or tag_id)
                try:
                    exif_summary[tag_name] = str(value)
                except Exception:
                    # Skip EXIF tags that can't be converted to string
                    pass

            return {
                "path": path,
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
                "format": img.format,
                "file_size": stat.st_size,
                "exif_keys": list(exif_summary.keys()),
                "exif_summary": exif_summary,
            }
    except Exception as e:
        return {"error": str(e)}


def compute_hash(path: str, hash_type: str = "phash") -> dict:
    """Return perceptual hash for an image."""
    try:
        from PIL import Image
        import os

        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}

        with Image.open(path) as img:
            img = img.convert("L").resize((32, 32))
            pixels = list(img.getdata())
            avg = sum(pixels) / len(pixels)
            bits = 0
            for i, pixel in enumerate(pixels):
                if pixel > avg:
                    bits |= (1 << i)

            return {
                "path": path,
                "hash_type": hash_type,
                "hash": hex(bits),
                "hash_int": bits,
            }
    except Exception as e:
        return {"error": str(e)}


def extract_features(path: str) -> dict:
    """Return 128-dim feature vector for visual search."""
    try:
        from PIL import Image
        import numpy as np
        import os

        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}

        img = Image.open(path).convert("RGB").resize((64, 64))
        arr = np.array(img)

        # Color histogram features (96 dims)
        hist_features = []
        for channel in range(3):
            hist, _ = np.histogram(arr[:, :, channel].flatten(), bins=32, range=(0, 255))
            hist_features.extend((hist / hist.sum()).tolist())

        # Edge density features (16 dims)
        gray = np.mean(arr, axis=2)
        edge_density = []
        grid_size = 16
        for i in range(4):
            for j in range(4):
                region = gray[i*grid_size:(i+1)*grid_size, j*grid_size:(j+1)*grid_size]
                edge_density.append(float(np.var(region) / 255.0))

        # Brightness features (16 dims)
        brightness_features = []
        for channel in range(3):
            channel_data = arr[:, :, channel].flatten()
            brightness_features.extend([
                float(np.mean(channel_data) / 255.0),
                float(np.std(channel_data) / 255.0),
                float(np.percentile(channel_data, 25) / 255.0),
                float(np.percentile(channel_data, 75) / 255.0),
                float(np.max(channel_data) / 255.0),
                float(np.min(channel_data) / 255.0),
            ])
        while len(brightness_features) < 16:
            brightness_features.append(0.0)

        features = np.array(hist_features + edge_density + brightness_features[:16], dtype=np.float32)
        norm = np.linalg.norm(features)
        if norm > 0:
            features = features / norm

        return {
            "path": path,
            "dimensions": len(features.tolist()),
            "features": features.tolist(),
        }
    except Exception as e:
        return {"error": str(e)}


def generate_thumbnail(path: str, size: str = "medium") -> dict:
    """Generate and cache thumbnail."""
    try:
        from PIL import Image
        import os

        sizes = {"small": 200, "medium": 800, "large": 1920}
        max_size = sizes.get(size, 800)

        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}

        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)
        thumb_path = os.path.join(THUMBNAIL_DIR, f"{name}_{size}{ext}")

        if os.path.exists(thumb_path):
            return {"path": thumb_path, "cached": True, "size": size}

        with Image.open(path) as img:
            img.thumbnail((max_size, max_size))
            img.save(thumb_path)

        return {"path": thumb_path, "cached": False, "size": size}
    except Exception as e:
        return {"error": str(e)}


# MCP Tool Definitions
TOOLS = [
    {
        "name": "analyze_image",
        "description": "Return image properties: dimensions, format, file size, EXIF summary",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to image file"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "compute_hash",
        "description": "Return perceptual hash for an image (pHash)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to image file"},
                "hash_type": {"type": "string", "description": "Hash type (default: phash)"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "extract_features",
        "description": "Return 128-dim feature vector for visual search",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to image file"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "generate_thumbnail",
        "description": "Generate and cache thumbnail for an image",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to image file"},
                "size": {"type": "string", "description": "Thumbnail size: small, medium, large"},
            },
            "required": ["path"],
        },
    },
]


def handle_tool_call(name: str, arguments: dict) -> dict:
    """Route tool call to appropriate function."""
    if name == "analyze_image":
        return analyze_image(arguments["path"])
    elif name == "compute_hash":
        return compute_hash(arguments.get("path"), arguments.get("hash_type", "phash"))
    elif name == "extract_features":
        return extract_features(arguments["path"])
    elif name == "generate_thumbnail":
        return generate_thumbnail(arguments["path"], arguments.get("size", "medium"))
    else:
        return {"error": f"Unknown tool: {name}"}


if __name__ == "__main__":
    # Simple MCP server loop (reads JSON from stdin, writes JSON to stdout)
    import sys

    def send_response(response: dict):
        json.dump(response, sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()

    # Send tools list
    send_response({"tools": TOOLS})

    # Process tool calls
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            tool_name = request.get("tool")
            arguments = request.get("arguments", {})
            result = handle_tool_call(tool_name, arguments)
            send_response({"tool": tool_name, "result": result})
        except Exception as e:
            send_response({"error": str(e)})

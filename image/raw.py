from __future__ import annotations
from pathlib import Path

def raw_available():
    try:
        import rawpy
        return True
    except ImportError:
        return False

def load_raw(path, half_size=False):
    import numpy as np
    try:
        import rawpy
    except ImportError as exc:
        raise RuntimeError("RAW support is not installed. Run: pip install rawpy") from exc

    path = Path(path)
    rgb = load_raw_pixels(path, half_size=half_size)
    if rgb.dtype == np.uint16:
        rgb = (rgb / 257).round().astype(np.uint8)
    from PIL import Image
    return Image.fromarray(rgb, "RGB")


def load_raw_pixels(path, half_size=False):
    """Develop a RAW file to sRGB, retaining 16-bit channels for full-size work."""
    try:
        import rawpy
    except ImportError as exc:
        raise RuntimeError("RAW support is not installed. Run: pip install rawpy") from exc

    path = Path(path)
    with rawpy.imread(str(path)) as raw:
        options = dict(
            use_camera_wb=True,
            use_auto_wb=False,
            no_auto_bright=True,
            output_bps=8 if half_size else 16,
            half_size=half_size,
            output_color=rawpy.ColorSpace.sRGB,
            highlight_mode=rawpy.HighlightMode.Blend,
        )
        if not half_size:
            options["demosaic_algorithm"] = rawpy.DemosaicAlgorithm.AHD
        return raw.postprocess(**options)

def raw_metadata(path):
    try:
        import rawpy
        with rawpy.imread(str(path)) as raw:
            return {
                "raw": True,
                "camera_white_balance": True,
                "black_level": list(getattr(raw, "black_level_per_channel", [])),
                "white_level": int(getattr(raw, "white_level", 0)),
                "sizes": str(getattr(raw, "sizes", "")),
            }
    except Exception:
        return {"raw": True}

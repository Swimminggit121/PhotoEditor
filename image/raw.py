from __future__ import annotations
from pathlib import Path

def raw_available():
    try:
        import rawpy
        return True
    except ImportError:
        return False

def load_raw(path):
    try:
        import rawpy
    except ImportError as exc:
        raise RuntimeError("RAW support is not installed. Run: pip install rawpy") from exc

    path = Path(path)
    with rawpy.imread(str(path)) as raw:
        rgb = raw.postprocess(
            use_camera_wb=True,
            use_auto_wb=False,
            no_auto_bright=False,
            output_bps=16,
            half_size=False,
            output_color=rawpy.ColorSpace.sRGB,
            demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
        )
    from PIL import Image
    return Image.fromarray(rgb).convert("RGB")

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

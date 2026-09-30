# PhotoEditor

PhotoEditor is a Windows desktop photo editor built with Python, PySide6, Pillow, NumPy and OpenCV. It is designed around a non-destructive editing workflow with a Lightroom-style development interface.

## Current features

- JPG, JPEG, PNG, TIFF, WebP, BMP and GIF raster import
- Optional RAW import through rawpy
- Exposure, contrast, highlights, shadows, whites and blacks
- Temperature, tint, saturation and vibrance
- Texture, clarity and dehaze
- Sharpening and noise reduction
- Grain and vignette
- HSL colour mixer
- RGB/master curves
- Shadows, midtones, highlights and global colour grading
- Colour grading blending and balance
- Automatic colour correction / Auto Colour Grade
- Rotate, straighten and flip
- Crop presets: original, 1:1, 4:3, 16:9 and 3:4
- Before/after preview
- Zoom, fit and canvas panning
- Histogram
- Undo/redo and reset
- Non-destructive adjustment state
- Save and reopen .photoedit projects
- JPEG, PNG, TIFF and WebP export
- Export quality control
- Preset storage API
- Batch processing API
- Image metadata reading API

## Optional RAW support

The main requirements are kept compatible with the project's Python 3.14 environment. To add RAW decoding, install:

```bash
pip install -r requirements-raw.txt
```

If rawpy is unavailable, normal raster image editing still works.

## Run

```bash
python main.py
```

## Project layout

- `app/` application and main window
- `core/` document, history, renderer, projects and automatic grading
- `image/` loading, exporting and metadata
- `processing/` image-processing algorithms and batch processing
- `ui/` editor panels and controls
- `presets/` preset storage
- `tests/` automated smoke tests

## Development

The editor is intentionally split into non-destructive processing stages so new tools can be added without changing the original image. Export always renders the current adjustment state.

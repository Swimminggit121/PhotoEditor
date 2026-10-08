# PhotoEditor

PhotoEditor is a Windows-focused, non-destructive photo editor built with Python and PySide6.

## Editing

- Exposure, contrast, highlights, shadows, whites and blacks
- Temperature, tint, vibrance and saturation
- Texture, clarity, dehaze, sharpening and noise reduction
- Curves and HSL
- Professional colour grading controls
- Local brush, linear and radial adjustments
- Cropping, geometry and export
- RAW image loading where supported
- Batch auto-editing
- Before/after preview and history

## AI Studio

The editor now includes an optional local AI subsystem. The normal editor remains usable without AI packages.

AI features include:

- Object and subject detection
- Face-aware focal point detection
- AI subject masks
- Sky masks
- Smart aspect-ratio cropping
- Photo quality analysis
- Exposure, sharpness, noise and composition scoring
- AI-assisted auto grading
- Reference-image matching
- Duplicate/burst analysis
- Batch photo ranking and culling
- Local denoising and upscaling pipeline
- GPU/CPU runtime detection
- Model caching under the user's PhotoEditor AI directory

AI models are loaded locally. The application does not require sending photographs to a cloud AI service.

## Optional AI installation

Use Python 3.13 for the most predictable Windows AI environment.

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-ai.txt
```

The first detector inference can download its model automatically. Model files are kept outside the repository so they are not bundled into Git or every Windows executable.

For NVIDIA systems, the installed PyTorch build should provide CUDA support; PhotoEditor automatically selects CUDA when PyTorch reports a CUDA-capable device and otherwise uses CPU.

## Run

```powershell
python main.py
```

## Windows build

GitHub Actions builds:

- PhotoEditor.exe
- VideoEditor.exe
- PhotoEditorSuite.exe

The base Windows executable deliberately does not bundle large optional AI model weights. Install the optional AI environment separately when local AI features are required.

## Project structure

```
ai/             Local AI runtime, analysis, masks, culling and enhancement
app/            Application/window lifecycle
core/           Document, rendering, history and photo intelligence
image/          Image/RAW loading and export
masks/          Local adjustment mask engine
processing/     Image processing algorithms
ui/             PySide6 interface
tests/          Smoke and feature tests
.github/        CI and Windows build automation
```

# PhotoEditor

PhotoEditor is a Windows-focused, non-destructive photo editor built with Python and PySide6.

## Editing

- Exposure, contrast, highlights, shadows, whites and blacks
- Temperature, tint, vibrance and saturation
- Texture, clarity, dehaze, sharpening and noise reduction
- Curves, HSL and professional colour grading
- Local brush, linear and radial adjustments
- Cropping, geometry, RAW loading where supported, and export
- Batch auto-editing, before/after preview and history

## AI Studio

The optional local AI subsystem supports object detection, face-aware focal points, sky heuristics, smart crops, quality scoring, exposure suggestions, duplicate/burst analysis, batch ranking and reference-image matching. Some features are conventional computer-vision heuristics rather than learned AI. The current subject mask combines an object-detection box with GrabCut; it is not equivalent to a dedicated segmentation model.

Photos are processed locally. The first use of the AI detector requires an internet connection to download model files; subsequent use can run locally from the model cache.

## AI model and licensing status

The YOLO/Ultralytics dependency has been removed from the AI branch. Object detection uses facebook/detr-resnet-50 through Hugging Face Transformers.

- **Application licence:** LICENSE contains PhotoEditor's custom source-available licence. It permits use of the application and commercial use of edited photographs, but reserves paid official distribution to the copyright holder while permitting free sharing by recipients.
- **Implementation code:** Hugging Face Transformers is licensed under Apache-2.0. DETR model implementation is provided through Transformers.
- **Model weights:** the official facebook/detr-resnet-50 repository declares Apache-2.0 and provides SafeTensors weights. The application requests SafeTensors rather than legacy pickle weights.
- **Training-data provenance:** the model card says the model was trained on COCO 2017. Dataset terms and provenance are a separate question from the model repository's declared licence and must be reviewed before commercial distribution.
- **Other dependencies:** PyTorch, torchvision, Hugging Face Hub, SafeTensors and all bundled libraries retain their own licences. See THIRD_PARTY_NOTICES.md and re-check versions before each public release.

The copyright holder may charge for official editions under the updated custom licence; recipients may share free copies but may not resell the application. The licence audit is an engineering checklist, not legal advice. The custom PhotoEditor licence is source-available and is not an OSI-approved open-source licence.

## Optional AI installation

Use Python 3.13 for the most predictable Windows AI environment.

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-ai.txt
```

For GPU acceleration, the AI edition bundles a CUDA-capable PyTorch runtime and automatically selects CUDA when a compatible NVIDIA GPU and driver are available; otherwise it selects CPU. The standard edition remains separate and lightweight. GitHub-hosted CI does not provide a physical NVIDIA GPU, so actual GPU inference and CPU fallback still need to be validated on Windows hardware before public release.

## Run

```powershell
python main.py
```

## Windows build

GitHub Actions builds PhotoEditor.exe, VideoEditor.exe and PhotoEditorSuite.exe, plus a separate PhotoEditor-AI-Windows.zip bundle containing PhotoEditor-AI.exe and its CUDA-capable runtime. The AI bundle downloads DETR weights on first AI use rather than embedding model weights into the release archive. The release workflow includes an executable-size guard and a separate ALLOW_AI_RELEASE approval gate while dataset provenance, final packaging, and CUDA-enabled executable support remain under review.

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

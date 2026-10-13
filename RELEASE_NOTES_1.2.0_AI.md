# PhotoEditor 1.2.0 — AI Windows Build

This release adds a dedicated consumer-friendly **PhotoEditor-AI.exe**.

## Consumer experience

- One Windows executable.
- No Python installation.
- No virtual environment.
- No separate AI runtime setup.
- A compact CPU-enabled PyTorch runtime is bundled so the single-file download stays below GitHub's 2 GiB per-asset limit.
- The packaged executable uses CPU inference; CUDA acceleration is available only in a separately configured Python environment with a CUDA-enabled PyTorch build.
- YOLO11 segmentation/object detection is bundled with the executable.
- The bundled model is copied to the user's PhotoEditor AI cache on first AI use.
- Larger optional models remain outside the executable so the main download stays practical.

## AI features in this build

- Subject/object detection.
- Person and face-aware analysis.
- Subject masking.
- Sky masking.
- Smart crop with detected subject positioning.
- Image quality scoring.
- Sharpness/noise/exposure/composition analysis.
- AI-assisted grading.
- Reference matching.
- Local denoise.
- Upscaling.
- AI model caching.

## Files

- `PhotoEditor-AI.exe` — recommended build for users who want AI.
- `PhotoEditor.exe` — standard lightweight build.
- `VideoEditor.exe`
- `PhotoEditorSuite.exe`

The AI executable is intentionally a single-file Windows application. Heavy optional VLM/embedding models are downloaded only when those advanced capabilities are enabled in future AI modules.

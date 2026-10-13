# PhotoEditor 1.2.0 — AI Windows Build

This branch is preparing a consumer-friendly PhotoEditor-AI.exe.

## Current architecture

- The base editor remains usable without AI dependencies.
- Object detection uses facebook/detr-resnet-50 through Hugging Face Transformers.
- DETR weights are downloaded on first AI use and cached locally.
- SafeTensors loading is required; legacy pickle-based checkpoints are not requested.
- The AI executable currently bundles CPU-only PyTorch to keep packaging predictable. It does not use CUDA.
- In a Python environment with a compatible CUDA-enabled PyTorch build and NVIDIA driver, the AI runtime selects CUDA automatically and falls back to CPU if CUDA is unavailable.

## AI capabilities and limitations

- Object detection and subject focal-box estimation.
- Face-aware analysis using the existing OpenCV cascade fallback.
- Subject masking by combining detection boxes with GrabCut; this is not a dedicated learned segmentation model.
- Sky masking using a colour/position heuristic, not learned semantic segmentation.
- Smart crop, image quality scoring, exposure suggestions, AI-assisted grading, reference matching, local denoise and upscaling pipeline.
- Model caching and offline inference after model files have been downloaded.

## Licensing status

- YOLO/Ultralytics code and weights have been removed from the intended AI runtime.
- The official facebook/detr-resnet-50 model repository declares Apache-2.0 and provides SafeTensors weights.
- COCO 2017 dataset provenance/terms and the complete frozen-executable dependency inventory still require review.
- Public AI release is gated by the ALLOW_AI_RELEASE repository variable until the remaining licensing and packaging checks are complete.
- The PhotoEditor custom licence permits the copyright holder to sell official editions; recipients may share free copies but may not resell the application. This custom licence should receive qualified legal review before commercial distribution.

## Planned assets after verification

- PhotoEditor.exe — standard lightweight build.
- PhotoEditor-AI.exe — AI-enabled CPU build.
- VideoEditor.exe
- PhotoEditorSuite.exe

The AI build is not considered release-ready until Windows tests, size checks, first-run model download, cached inference, notices and the release gate have been reviewed.

# PhotoEditor 1.2.0 — AI Windows Build

This branch prepares a consumer-friendly AI-enabled Windows bundle. The standard PhotoEditor.exe remains separate and lightweight.

## AI runtime

- Object detection uses facebook/detr-resnet-50 through Hugging Face Transformers.
- The model is pinned to revision `1d5f47bd3bdd2c4bbfa585418ffe6da5028b4c0b`.
- SafeTensors loading is required; legacy pickle-based checkpoints are not requested.
- The AI bundle uses CUDA-capable PyTorch. The runtime selects CUDA when a compatible NVIDIA driver/GPU is available and falls back to CPU otherwise.
- The Windows bundle is packaged as `PhotoEditor-AI-Windows.zip`; extract the folder and run `PhotoEditor-AI.exe` from inside it. Do not move the executable away from its accompanying runtime files.
- DETR weights download on first AI use and are cached locally. Subsequent inference can run from the cache without a network connection.

## AI capabilities and limitations

- Object detection and subject focal-box estimation.
- Face-aware analysis using the existing OpenCV cascade fallback.
- Subject masking by combining detection boxes with GrabCut; this is not a dedicated learned segmentation model.
- Sky masking using a colour/position heuristic, not learned semantic segmentation.
- Smart crop, image quality scoring, exposure suggestions, reference-image matching, local denoise and conventional high-quality resizing.
- Model caching and offline inference after model files have been downloaded.

## Licensing status

- YOLO/Ultralytics code and weights have been removed from the intended AI runtime.
- The official facebook/detr-resnet-50 model repository declares Apache-2.0 and provides SafeTensors weights.
- COCO 2017 dataset provenance/terms and the complete frozen-executable dependency inventory still require review.
- Public AI release is gated by the `ALLOW_AI_RELEASE` repository variable until the remaining licensing and packaging checks are approved.
- The PhotoEditor custom licence reserves paid official distribution to the copyright holder; recipients may share free copies but may not resell the application. Obtain qualified legal review before commercial distribution.

## Planned release assets after verification

- PhotoEditor.exe — standard photo editor.
- PhotoEditor-AI-Windows.zip — AI executable and its CUDA-capable runtime folder.
- VideoEditor.exe
- PhotoEditorSuite.exe

The AI build is not release-ready until CI tests pass, the bundle size is acceptable, first-run model download and cached inference are checked, and NVIDIA GPU plus CPU fallback are tested on Windows.

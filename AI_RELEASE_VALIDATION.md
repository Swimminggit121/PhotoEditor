# PhotoEditor AI release validation checklist

Do not publish the AI edition until every required check below is complete. The GitHub Actions release gate must remain disabled while any licensing, packaging, or hardware check is open.

## Automated checks

- [ ] Latest `PhotoEditor CI` run passes all smoke, feature, batch, export, photo-intelligence, video, compile and AI fallback tests.
- [ ] CUDA-capable PyTorch installs successfully on the Windows runner.
- [ ] The pinned model revision matches the configured revision.
- [ ] Downloaded `model.safetensors` matches the SHA-256 in `AI_MODEL_MANIFEST.json`.
- [ ] AI onedir package builds and the ZIP remains below the configured size guard.
- [ ] The ZIP contains `PhotoEditor-AI.exe`, `THIRD_PARTY_NOTICES.md`, `AI_MODEL_MANIFEST.json`, and `third-party-licenses.json`.
- [ ] The regular PhotoEditor, VideoEditor and Suite EXEs build successfully.

## Physical Windows hardware checks

GitHub-hosted runners do not provide a physical NVIDIA GPU. Run these checks on a compatible Windows computer before claiming GPU acceleration is validated.

1. Extract the complete `PhotoEditor-AI-Windows.zip` folder; do not move the EXE out of its folder.
2. Launch `PhotoEditor-AI.exe` and open a normal image.
3. Trigger AI analysis with an internet connection and verify the pinned model downloads without a checksum error.
4. Close and reopen the app, disconnect from the internet, and confirm cached model inference still works.
5. On a compatible NVIDIA system, verify `torch.cuda.is_available()` is true in the packaged runtime and run object detection. Confirm the runtime manifest records `runtime_device: cuda`.
6. On a system without a compatible NVIDIA GPU/driver, verify inference runs on CPU and records `runtime_device: cpu`.
7. Check the UI remains responsive during model loading and analysis, and verify errors are shown clearly rather than silently reported as successful.
8. Check the package on a clean Windows account or VM without a Python installation.

## Licensing and distribution checks

- [ ] A qualified reviewer has assessed the custom PhotoEditor licence before commercial distribution.
- [ ] A qualified reviewer has assessed DETR/COCO training-data provenance and the implications of commercial distribution. COCO annotations are CC BY 4.0; COCO images remain under original rights-holder/Flickr terms. These facts alone do not settle every question about model training.
- [ ] Review the generated dependency licence inventory and preserve all notices/licence texts required by the exact bundled versions.
- [ ] Confirm no YOLO/Ultralytics packages, weights, or downloads are present in the release branch or final artifacts.
- [ ] Confirm the release ZIP contents and file sizes from the actual successful CI artifact.

## GitHub release publishing

The workflow already declares `contents: write`, but a previous release publish attempt returned HTTP 403. If publishing still fails after the release gate is deliberately approved, check the repository's Actions workflow-permission setting and any organisation policy that may restrict the workflow token. Do not place personal access tokens or other secrets in source code.

Only after the checks above are approved should the repository variable `ALLOW_AI_RELEASE` be set to `true` and a version tag be pushed. Do not enable it just to test packaging.

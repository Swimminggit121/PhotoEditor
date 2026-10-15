# PhotoEditor AI release validation checklist

Do not push changes to the designated release branch until every required check below is complete. The `ALLOW_AI_RELEASE` variable gates AI uploads from version tags, but the `release/1.2.0-ai` branch publishes to `v1.2.0` without that variable.

## Automated checks

- [x] CI run [38393873581](https://github.com/Swimminggit121/PhotoEditor/actions/runs/38393873581) passed smoke, feature, batch, export, photo-intelligence, video, compile and AI fallback tests on Windows.
- [x] CUDA-capable PyTorch installed successfully on the Windows runner; the runner itself did not provide a physical NVIDIA GPU.
- [x] The pinned model revision matched the configured revision.
- [x] Downloaded `model.safetensors` matched the SHA-256 in `AI_MODEL_MANIFEST.json`.
- [x] AI onedir package built and the ZIP passed the configured size guard.
- [x] Downloaded and inspected the actual CI artifact: the inner ZIP contains `PhotoEditor-AI.exe`, `THIRD_PARTY_NOTICES.md`, `AI_MODEL_MANIFEST.json`, and `third-party-licenses.json`; the ZIP contains 15,702 entries and is about 314.9 MiB.
- [x] The regular PhotoEditor, VideoEditor and Suite EXEs built successfully.

**Evidence:** CI run `38393873581`, commit `981157e2334267dae7b3a768103a54acf7e29166`. The artifact was inspected as an archive, not executed on Windows hardware. The generated inventory contains 49 package entries and no package names matching YOLO/Ultralytics.

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
- [x] Source/build workflow and the actual generated package inventory were checked for YOLO/Ultralytics; no YOLO/Ultralytics package names were found in the bundled 49-entry dependency inventory. Repeat a complete source/artifact scan before public release.
- [x] Confirmed the actual successful CI artifact's nested ZIP contents and size (about 314.9 MiB; 15,702 entries).

## GitHub release publishing

The workflow already declares `contents: write`, but a previous release publish attempt returned HTTP 403. If publishing fails, check the repository's Actions workflow-permission setting and any organisation policy that may restrict the workflow token. Do not place personal access tokens or other secrets in source code.

The designated `release/1.2.0-ai` branch publishes its AI ZIP to the `v1.2.0` release after both the AI build and standard release jobs succeed. Complete the open licensing and physical-hardware checks before pushing changes to this branch. Other `v*` tags publish an AI ZIP only when the repository variable `ALLOW_AI_RELEASE` is `true`; do not enable it just to test packaging.

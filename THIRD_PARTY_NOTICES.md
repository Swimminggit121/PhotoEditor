# Third-party software and model notices

This inventory is for the AI release branch. Verify exact versions, artefacts, and upstream notices again before each public release. This document is not legal advice. The application custom licence reserves paid official distribution to the copyright holder; that term and its interaction with third-party licence obligations need qualified review before distribution.

## Archived AI build inventory review

The actual AI ZIP from CI run [38393873581](https://github.com/Swimminggit121/PhotoEditor/actions/runs/38393873581), commit `981157e2334267dae7b3a768103a54acf7e29166`, was downloaded and inspected. It contained 15,702 archive entries and was about 314.9 MiB. Its `third-party-licenses.json` had 49 package rows. This is build-environment package metadata, not a content-derived SBOM; it includes build tools and does not establish which files from each package are in the application.

| Component | Archived CI version | Generated licence metadata | Audit notes |
|---|---:|---|---|
| PhotoEditor | source at `981157e` | Custom licence in `LICENSE` | The inspected ZIP did not contain the project `LICENSE`. The build workflow now copies it and fails if it is missing; inspect a new artifact to verify. The no-resale term and distribution of the combined application need qualified review. |
| [PySide6, PySide6_Addons, PySide6_Essentials](https://doc.qt.io/qtforpython-6/licenses.html) | 6.12.0 | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | Qt DLLs are present in the ZIP. The generated JSON contained identifiers but no licence texts. The archive scan found no Qt/PySide licence text; identify applicable Qt component licences and satisfy their notice, source, relinking and user-modification obligations before distribution. |
| [PySide6_Pdf, PySide6_WebEngine](https://doc.qt.io/qtforpython-6/licenses.html) | 6.12.0.140 | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | Present in the package inventory; verify whether and how their Qt components are shipped and which notices apply. |
| [shiboken6](https://doc.qt.io/qtforpython-6/licenses.html) | 6.12.0 | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | Binding files are present. Confirm the selected licence path and required notices. |
| [PyTorch](https://github.com/pytorch/pytorch/blob/main/LICENSE) | 2.14.1 | `Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT` | The archive contains the PyTorch licence and numerous third-party licence files. Review bundled components and notices against this exact wheel. |
| [torchvision](https://github.com/pytorch/vision/blob/main/LICENSE) | 0.29.1 | `BSD` | The archive contains the wheel's `LICENSE`. |
| [Transformers](https://github.com/huggingface/transformers/blob/main/LICENSE) | 5.19.0 | `Apache 2.0 License` | The archive contains the wheel's `LICENSE`. |
| [SafeTensors](https://github.com/safetensors/safetensors/blob/main/LICENSE) | 0.8.0 | `Apache Software License` | Present in the generated inventory; verify packaged notices against the archive. |
| [Hugging Face Hub](https://github.com/huggingface/huggingface_hub/blob/main/LICENSE) | 2.2.0 | `Apache Software License` | Present in the generated inventory; verify packaged notices against the archive. |
| [OpenCV Python wheel](https://github.com/opencv/opencv/blob/4.x/LICENSE) | 5.0.0.93 | `Apache Software License` | The archive contains the wheel's `LICENSE.txt`. |
| [Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE) | 12.3.0 | `MIT-CMU` | The archive contains the wheel's `LICENSE`; the former HPND description did not match this artifact. |
| [NumPy](https://github.com/numpy/numpy/blob/main/LICENSE.txt) | 2.5.4 | `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | The archive contains multiple NumPy and vendored-component licence files. Review these files for the exact wheel. |
| [PyInstaller](https://pyinstaller.org/en/stable/license.html) | 6.22.3 | `GNU General Public License v2 (GPLv2)` | A build tool, not a Python runtime package in the ZIP. PyInstaller documents a GPL exception for generated executables; verify the exact release's `COPYING.txt` and bundled bootloader components. |

The workflow now asks `pip-licenses` to include available licence-file paths and texts in the JSON for subsequent builds. This does not establish that every bundled component or obligation is covered. The prior ZIP included `THIRD_PARTY_NOTICES.md`, `AI_MODEL_MANIFEST.json`, and the 49-row JSON, but a new artifact is needed to verify the updated inventory and added application `LICENSE`.

## Model and dataset provenance

The pinned [model card](https://huggingface.co/facebook/detr-resnet-50/tree/1d5f47bd3bdd2c4bbfa585418ffe6da5028b4c0b) declares Apache-2.0 for `facebook/detr-resnet-50` and says it was trained on COCO 2017. The [COCO Terms of Use](https://cocodataset.org/#termsofuse) distinguish annotations from images whose copyrights remain with their original rights holders and whose use is governed by applicable original terms. These declarations do not establish the rights or legal implications of model training, the weights, or commercial model distribution. Qualified legal review is still required.

For Qt for Python, see [Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html), [Qt licensing](https://doc.qt.io/qt-6/licensing.html), and the [LGPL-3.0 text](https://spdx.org/licenses/LGPL-3.0-only.html). For PyInstaller's build-tool exception, see its [licence page](https://pyinstaller.org/en/stable/license.html). These references are technical sources, not a determination that this package complies with them.

## Explicitly removed from this branch

- Ultralytics package and YOLO model weights are no longer intended parts of the AI runtime.
- No YOLO weights should be bundled or downloaded by this branch. Search source, requirements, workflow logs and built artifacts before release to verify no stale references remain.

## Release validation checklist

- [x] Confirmed by source/requirements/build-workflow scan that no Ultralytics/YOLO imports, dependencies, downloads or bundled model files remain in this AI branch.
- [x] Pin the model to immutable revision `1d5f47bd3bdd2c4bbfa585418ffe6da5028b4c0b` and verify that revision has SafeTensors weights in CI.
- [x] Record the pinned SafeTensors SHA-256 checksum in `ai/config.py`, verify it in CI and verify it again before first model use; record it in the local runtime manifest.
- [x] Inspected the archived AI ZIP and its generated 49-row inventory from CI run [38393873581](https://github.com/Swimminggit121/PhotoEditor/actions/runs/38393873581), commit `981157e2334267dae7b3a768103a54acf7e29166`.
- [x] Compared archived package metadata and selected bundled licence paths for Qt for Python, PyTorch, torchvision, Transformers, OpenCV, Pillow and NumPy; details and exact versions are listed above.
- [ ] Inspect a new AI ZIP after the workflow change to verify it contains the project `LICENSE` and generated licence texts.
- [ ] Identify all shipped Qt/PySide and other bundled third-party components, select applicable licensing terms, and verify required notices, source/relinking materials and user rights are delivered. The archived ZIP included Qt DLLs but no Qt/PySide licence text was found.
- [ ] Obtain qualified review of the custom application licence, its no-resale restriction as applied to the combined application, and all third-party distribution terms.
- [ ] Obtain qualified review of DETR weights/training-data provenance and implications of commercial distribution. The model card's Apache-2.0 declaration and COCO's published terms do not resolve this question.
- [ ] Run AI, mask, smoke and packaging tests on Windows.
- [x] Verified the archived AI ZIP size and package-file presence; this does not establish successful execution of the packaged application.
- [ ] Verify first-run model download, offline cached inference, CPU inference and clean-account execution using the packaged application.
- [ ] Verify CUDA inference on physical NVIDIA hardware. The available Windows environment has Intel UHD graphics, no `nvidia-smi`, and no installed PyTorch; hosted CI also had no physical NVIDIA GPU. GPU support is unverified.
- [ ] Do not describe the current heuristic sky mask or GrabCut mask as a fully learned segmentation model.

## GitHub release publishing

The designated `release/1.2.0-ai` branch publishes its AI ZIP to the `v1.2.0` release after both the AI build and standard release jobs succeed. Other `v*` tags publish an AI ZIP only when the repository variable `ALLOW_AI_RELEASE` is `true`. Publishing an experimental build does not clear the outstanding legal, packaging, or hardware items above.

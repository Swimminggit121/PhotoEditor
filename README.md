# PhotoEditor

PhotoEditor is a Windows-focused photo-editing suite built with Python and PySide6. It is designed for non-destructive editing, practical colour correction, local adjustments, batch workflows and export. This repository also contains a separate AI-enabled edition in active development.

> **Project status:** the AI edition is experimental and is not yet a verified public release. The latest Windows CI build must finish successfully, and GPU/CPU behaviour must be tested on real Windows hardware before the AI bundle can be considered release-ready. The lightweight standard edition and AI edition are separate builds.

## Contents

- [Features](#features)
- [Editions and downloads](#editions-and-downloads)
- [Install and run from source](#install-and-run-from-source)
- [Using PhotoEditor](#using-photoeditor)
- [AI Studio](#ai-studio)
- [AI model, privacy and network use](#ai-model-privacy-and-network-use)
- [Performance and GPU support](#performance-and-gpu-support)
- [Build Windows executables](#build-windows-executables)
- [Tests and continuous integration](#tests-and-continuous-integration)
- [Troubleshooting](#troubleshooting)
- [Repository layout](#repository-layout)
- [Licensing and third-party notices](#licensing-and-third-party-notices)
- [Known limitations and roadmap](#known-limitations-and-roadmap)
- [Contributing and reporting problems](#contributing-and-reporting-problems)

## Features

### Photo editing

The application code includes tools for:

- **Light and tone:** exposure, contrast, highlights, shadows, whites and blacks.
- **Colour:** temperature, tint, saturation, vibrance, HSL controls, curves and colour grading.
- **Detail:** texture, clarity, dehaze, sharpening and noise-reduction controls.
- **Local adjustments:** brush, linear and radial masks, with a mask/adjustment workflow.
- **Composition:** crop and geometry tools.
- **Workflow:** image preview, before/after comparison, history, presets, batch auto-editing and export.
- **Formats:** common image formats and RAW loading where the installed RAW support and camera format allow it.

The exact controls available depend on the current application UI and the file format. Always review the exported result: editing operations can change image appearance and some export formats do not preserve every source-image property or metadata field.

### Other tools in this repository

The repository also contains a video editor entry point and a suite entry point. These are built as separate Windows executables by the standard Windows build workflow.

## Editions and downloads

| Edition | Intended use | Status |
|---|---|---|
| **PhotoEditor** | Standard photo editor with a lighter dependency set | Built by the standard Windows workflow |
| **PhotoEditor AI** | Standard editor plus optional local AI analysis features | Experimental; release gate remains closed until validation is complete |
| **VideoEditor** | Separate video-editor entry point | Built by the standard Windows workflow |
| **PhotoEditor Suite** | Suite entry point | Built by the standard Windows workflow |

### Where to get a Windows build

- Check [GitHub Releases](https://github.com/Swimminggit121/PhotoEditor/releases) for published downloads.
- Check [GitHub Actions](https://github.com/Swimminggit121/PhotoEditor/actions) for build status and CI artifacts. Artifacts are temporary CI outputs and are not the same as a supported public release.
- Browse the [AI development branch](https://github.com/Swimminggit121/PhotoEditor/tree/release/1.2.0-ai) for the current experimental AI work.

**AI ZIP installation:** when an AI bundle is published, download `PhotoEditor-AI-Windows.zip`, extract the *entire* folder, and run `PhotoEditor-AI.exe` from inside the extracted folder. Keep the EXE beside its supporting runtime files; do not move the EXE on its own. The model weights are downloaded on first AI use and are not embedded in the ZIP, so the first AI run requires an internet connection.

Do not assume an unpublished artifact is stable or ready for everyday use. No new AI release should be considered official until the release checklist has been approved.

## Install and run from source

### Requirements

- Windows is the primary target for packaged builds.
- Python **3.13** is the version currently used by CI.
- Git, if you want to clone the repository or contribute changes.
- An internet connection for installing dependencies and downloading the AI model the first time it is needed.
- Additional disk space for Python packages, PyTorch and the cached AI model if you install the AI dependencies.

### Standard edition

Open PowerShell in the cloned repository folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

If PowerShell blocks virtual-environment activation, you can invoke the virtual-environment interpreter directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### Optional AI dependencies

Install the standard dependencies first, then install the AI requirements:

```powershell
python -m pip install -r requirements-ai.txt
python main.py
```

The AI dependency file includes PyTorch, torchvision, Transformers, SafeTensors and Hugging Face Hub. Package compatibility and GPU support depend on the selected PyTorch build, Windows driver and hardware. If you are setting up CUDA manually, use the official [PyTorch installation selector](https://pytorch.org/get-started/locally/) to select a compatible build. Do not install random third-party wheels.

To launch the other entry points from source:

```powershell
python video_main.py
python suite_main.py
```

Run commands from the repository root so Python can find the application packages.

## Using PhotoEditor

A typical workflow is:

1. Launch PhotoEditor and open an image.
2. Make basic exposure and colour adjustments before fine detail work.
3. Use curves, HSL and colour grading for more targeted tonal or colour changes.
4. Apply local adjustments where supported; inspect mask edges at a useful zoom level.
5. Compare the edited image against the original.
6. Export to the required format and quality, then open the exported file to check it.

### Practical advice

- Keep an untouched copy of important originals.
- Do not assume every RAW camera model or every metadata field is supported.
- Review sharpening, denoise and local masks at 100% zoom where possible.
- For batch editing, inspect a sample from the beginning, middle and end of the batch before using all results.
- Export settings affect file size, visual quality, colour profile and metadata. Choose them for the destination (web, print, archive or client delivery).

## AI Studio

The optional AI subsystem is intended to help with image review and editing suggestions. The current branch includes or is building toward:

- Object detection using DETR through Hugging Face Transformers.
- Object/focal-box information to assist composition.
- Face-aware focal-point analysis using the existing OpenCV cascade fallback.
- A heuristic sky mask.
- Subject-mask assistance combining detection boxes and GrabCut.
- Image quality scoring and exposure suggestions.
- Smart-crop assistance.
- Duplicate/burst analysis and batch ranking.
- Reference-image comparison/matching.
- Conventional denoise and resizing assistance.

**Important accuracy note:** not every item above is a learned AI model. Sky detection is a colour/position heuristic, and the current subject-mask approach uses an object-detection box plus GrabCut. These can fail on complex backgrounds, hair, transparent objects, overlapping subjects, unusual lighting or subjects outside the detector's trained classes. Face detection may miss faces or detect false positives. Quality scores and editing suggestions are aids, not objective truth.

AI features can be slower on CPU, particularly on large images. Start with a normal-sized image when testing the AI edition.

## AI model, privacy and network use

- **Model:** `facebook/detr-resnet-50`, loaded through Hugging Face Transformers.
- **Revision:** pinned to `1d5f47bd3bdd2c4bbfa585418ffe6da5028b4c0b` in the AI configuration.
- **Weights:** SafeTensors are requested rather than legacy pickle-based model weights.
- **Integrity:** the application and CI are configured to compare the downloaded model file against the SHA-256 value recorded in `ai/config.py`. A mismatch should stop model loading. CI must pass this check before release.
- **First run:** the model files are downloaded from Hugging Face when AI inference first needs them. This requires a working internet connection.
- **Later runs:** the model is cached locally, so inference can work without an internet connection as long as the required files remain cached.
- **Image privacy:** AI inference is intended to run locally in the application. The first-run model download contacts Hugging Face to retrieve model files; that is separate from uploading a user's photo. Do not use sensitive images with an experimental build unless you have reviewed the code and your own environment.
- **Manifest:** `AI_MODEL_MANIFEST.json` documents model identity, revision, checksum and known provenance caveats. `THIRD_PARTY_NOTICES.md` and `third-party-licenses.json` provide additional licensing information when included in a build.

The model repository declares Apache-2.0, but that statement does **not** automatically resolve every question about the model's training data, all bundled dependencies or every commercial use case. The model card identifies COCO 2017 as training data. COCO annotation licensing and the rights attached to individual images are distinct; the original image rights and training-data provenance require separate review. See [AI release validation checklist](AI_RELEASE_VALIDATION.md) and [third-party notices](THIRD_PARTY_NOTICES.md).

## Performance and GPU support

The AI runtime is designed to select CUDA when PyTorch reports a compatible NVIDIA GPU and driver, and otherwise fall back to CPU. This is the intended policy, not yet a substitute for real hardware validation.

- The standard edition is separate and intended to remain lighter.
- The AI Windows package uses an onedir layout because large ML runtimes are easier to package and diagnose as a folder.
- Run `PhotoEditor-AI.exe` from the extracted folder and keep all accompanying files in place.
- GitHub-hosted CI can check that a CUDA-capable PyTorch package is installed, but it does not provide a physical NVIDIA GPU. Successful CI alone cannot prove actual GPU inference works.
- Before the AI edition is described as fully supported, the packaged application must be tested on a compatible NVIDIA Windows PC and on a machine using CPU fallback. First-run download, cached/offline inference and a clean Windows installation also need validation.

## Build Windows executables

The GitHub Actions workflow is `.github/workflows/build.yml`.

The standard build creates:

- `PhotoEditor.exe`
- `VideoEditor.exe`
- `PhotoEditorSuite.exe`

The AI build is intended to create:

- `PhotoEditor-AI-Windows.zip`, containing `PhotoEditor-AI.exe`, its runtime files, `AI_MODEL_MANIFEST.json`, third-party notices and a generated dependency licence inventory.

The AI workflow checks the model revision, SafeTensors availability, SHA-256 checksum, package contents and ZIP size. The workflow may be changed as packaging issues are found; check the actual Actions run and its artifact rather than assuming a build succeeded.

### Build locally

Install the required dependencies and PyInstaller in the appropriate environment, then use the same entry points:

```powershell
python -m pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name PhotoEditor main.py
pyinstaller --noconfirm --clean --onefile --windowed --name VideoEditor video_main.py
pyinstaller --noconfirm --clean --onefile --windowed --name PhotoEditorSuite suite_main.py
```

The AI build uses a different onedir configuration in CI. For reliable AI packaging, use the workflow as the reference and test the resulting folder on a clean Windows machine. A successful PyInstaller command is not proof that every plugin, DLL or model dependency will work on another computer.

## Tests and continuous integration

The CI workflow runs on Windows and includes checks for:

- Application smoke and feature tests.
- Batch and social-export tests.
- Photo-intelligence and video tests.
- Python compile checks.
- AI fallback and model-metadata tests.
- Standard Windows executable builds.
- AI dependency installation, model revision and checksum validation, packaging and artifact upload.

Check the [Actions page](https://github.com/Swimminggit121/PhotoEditor/actions) for the current result. A run that is queued, pending, cancelled or still running is not a pass. A successful CPU/CI test does not replace physical NVIDIA testing.

Useful local test commands include:

```powershell
python tests/smoke_test.py
python tests/feature_test.py
python -m pytest -q tests/batch_test.py
python tests/social_export_test.py
python tests/photo_intelligence_test.py
python tests/video_test.py
python -m compileall -q ai app core image masks presets processing tests ui video main.py video_main.py suite_main.py
python tests/ai_test.py
```

## Troubleshooting

### The application does not launch

- Run it from PowerShell so startup errors remain visible.
- Confirm you are in the repository root and have installed `requirements.txt`.
- Use Python 3.13, which is the version used by CI.
- If using a packaged executable, extract the full ZIP and keep all files together.

### AI model download fails

- Check internet access and whether Hugging Face is reachable from your network.
- Retry after resolving proxy, firewall or certificate issues.
- Ensure the model cache has enough free disk space.
- If the checksum fails, do not bypass the check. Remove the affected cached checkpoint and retry; if it continues, report the error and the configured revision/checksum.

### CUDA is unavailable

- Check that the PC has a compatible NVIDIA GPU and current compatible driver.
- Check that the installed PyTorch build reports CUDA support.
- CUDA can be unavailable even when an NVIDIA GPU is present if the driver or PyTorch build is incompatible. The runtime should fall back to CPU; inference may be slower.
- Do not claim GPU acceleration is working until inference has actually run on the GPU.

### The AI ZIP fails to start

- Extract the complete ZIP into a writable folder.
- Do not move `PhotoEditor-AI.exe` separately.
- Try launching from PowerShell to capture the error.
- On a clean machine, Windows security software or missing system components may block startup; verify the artifact and error message before changing security settings.

### Photo import or RAW support fails

- Confirm the file is supported by the installed image/RAW dependencies.
- Try a copy converted to a common format such as PNG or JPEG to distinguish an import problem from an editing problem.
- Preserve the original file while investigating.

### CI build fails or a release returns HTTP 403

- Open the failed run and inspect the first failing step and its log.
- For release publishing, repository or organisation Actions token permissions may prevent creating releases even if the workflow requests `contents: write`.
- Do not commit personal access tokens or credentials. Keep the AI release gate closed until licensing, packaging and hardware validation are approved.

## Repository layout

```text
ai/                       AI model loading, runtime and image analysis
app/                      Application lifecycle and windows
core/                     Document, rendering, history and photo intelligence
image/                    Image/RAW loading and export
masks/                    Local-adjustment mask engine
processing/               Image-processing algorithms
presets/                  Built-in and user presets
ui/                       PySide6 interface and editing panels
video/                    Video-related code
tests/                    Automated tests
.github/workflows/build.yml
                          CI and Windows packaging workflow
AI_MODEL_MANIFEST.json    AI model identity and provenance notes
AI_RELEASE_VALIDATION.md  Pre-release checklist
THIRD_PARTY_NOTICES.md    Third-party licence and provenance notes
requirements.txt          Standard application dependencies
requirements-ai.txt       Optional AI runtime dependencies
```

## Licensing and third-party notices

The repository's `LICENSE` file contains a **custom source-available licence**, not an OSI-approved open-source licence. Read the full licence before copying, modifying, distributing or using the application commercially.

The intended terms are that people may use the app and may sell photographs or other creative work made with it, while paid distribution of the PhotoEditor program itself is reserved to the copyright holder. Recipients may share free copies subject to the licence. Do not assume that these plain-language notes replace the legal licence text.

Third-party libraries, model weights and other bundled components have their own terms. Read `THIRD_PARTY_NOTICES.md` and the dependency inventory shipped with a release. The AI edition is not cleared for commercial distribution merely because a model repository declares a particular licence. Qualified legal review of the custom application licence, model/data provenance and bundled dependencies remains outstanding.

## Known limitations and roadmap

Current known limits and release work include:

- Complete end-to-end validation of the AI Windows ZIP.
- Physical NVIDIA CUDA inference and CPU fallback testing.
- First-run model download and subsequent cached/offline inference testing.
- Review of the generated dependency licence inventory and all required notices.
- Qualified review of the custom licence and model-training/data provenance before commercial AI distribution.
- Continued improvement of learned segmentation: the current subject mask is detector-box plus GrabCut, and the sky mask is heuristic rather than a dedicated semantic segmentation model.
- Further testing of performance, UI responsiveness and clean-machine installation.

Do not treat an item as finished solely because it is mentioned in documentation. The release checklist and latest successful CI artifact are the source of truth for release readiness.

## Contributing and reporting problems

Bug reports are most useful when they include:

1. Windows version and Python version (for source installs).
2. Whether you used the standard or AI edition.
3. The steps that reproduce the issue.
4. The exact error message or relevant CI log.
5. For AI issues, whether the model was downloaded before, whether the PC has an NVIDIA GPU, and whether the runtime selected CUDA or CPU.

Please avoid attaching private photographs or other sensitive files unless you have checked that you are comfortable sharing them.

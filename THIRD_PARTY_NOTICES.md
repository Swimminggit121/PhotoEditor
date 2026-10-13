# Third-party software and model notices

This inventory is for the AI release branch. Verify exact versions, artefacts, and upstream notices again before each public release. This document is not legal advice.

| Component | Role | Code / artefact licence status | Source | Distribution note |
|---|---|---|---|---|
| PhotoEditor | Main application | Custom source-available licence in LICENSE | This repository | Use and commercial use of edited photos are permitted by the custom terms; selling the application itself is prohibited. |
| Hugging Face Transformers | DETR implementation and model loading | Apache-2.0 project licence | https://github.com/huggingface/transformers | Preserve required upstream notices for distributed components. |
| facebook/detr-resnet-50 | Pretrained object detector | Official model repository declares Apache-2.0; application requests SafeTensors weights | https://huggingface.co/facebook/detr-resnet-50 | Model card states training on COCO 2017. Review dataset provenance and terms separately. |
| PyTorch | Tensor operations and inference | Upstream BSD-style licence and notices apply | https://github.com/pytorch/pytorch | Verify exact installed wheel and bundled notices. |
| torchvision | Vision dependency | Upstream BSD-style licence and notices apply | https://github.com/pytorch/vision | Verify exact installed wheel and bundled notices. |
| SafeTensors | Checkpoint format | Apache-2.0 | https://github.com/huggingface/safetensors | Keep upstream notices for distributed copies. |
| Hugging Face Hub | Model download/cache client | Apache-2.0 | https://github.com/huggingface/huggingface_hub | Keep upstream notices for distributed copies. |
| OpenCV | Image operations and GrabCut | OpenCV licence; bundled components may have separate notices | https://github.com/opencv/opencv | Inspect selected wheel's bundled notices before distribution. |
| Pillow | Image loading/conversion | HPND licence | https://github.com/python-pillow/Pillow | Keep upstream notices for distributed copies. |
| NumPy | Numerical operations | BSD-style licence | https://github.com/numpy/numpy | Keep upstream notices for distributed copies. |

## Explicitly removed from this branch

- Ultralytics package and YOLO model weights are no longer intended parts of the AI runtime.
- No YOLO weights should be bundled or downloaded by this branch. Search source, requirements, workflow logs and built artifacts before release to verify no stale references remain.

## Release gate checklist

- [ ] Confirm no imports, dependencies, downloads or bundled files for Ultralytics/YOLO remain.
- [ ] Pin and record the exact Hugging Face model revision and SafeTensors checksum for each release.
- [ ] Review COCO 2017 dataset terms/provenance separately from the model repository's declared licence.
- [ ] Generate a licence inventory/SBOM for the exact frozen executable, including transitive packages and notices.
- [ ] Include required third-party notices and licence texts in release materials.
- [ ] Run AI, mask, smoke and packaging tests on Windows.
- [ ] Verify executable size, first-run model download, offline cached inference, CPU fallback and NVIDIA CUDA in a CUDA-enabled environment.
- [ ] Do not describe the current heuristic sky mask or GrabCut mask as a fully learned segmentation model.

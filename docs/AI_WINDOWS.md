# PhotoEditor AI for Windows

## Recommended consumer install

For a user who wants the AI features, download **PhotoEditor-AI.exe** from the latest GitHub release and run it.

There is no Python installation or manual model setup.

### GPU behaviour

PhotoEditor detects the available PyTorch backend automatically:

- NVIDIA CUDA GPU: use CUDA acceleration when available.
- No compatible NVIDIA GPU: use CPU automatically.

### AI model

PhotoEditor downloads the pinned DETR ResNet-50 model from Hugging Face when AI inference is first used. The weights are not included in the ZIP; the download is SHA-256 verified and cached locally. An internet connection is required for the first download. Later runs can use the cached model offline.

The exact model revision, checksum and provenance notes are documented in `AI_MODEL_MANIFEST.json`.

### Troubleshooting

If Windows security software blocks the application, use the normal Windows security review flow and only allow the executable if you trust the source.

If an NVIDIA GPU is not available, AI features continue through CPU fallback; processing will simply be slower.

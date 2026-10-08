# PhotoEditor AI for Windows

## Recommended consumer install

For a user who wants the AI features, download **PhotoEditor-AI.exe** from the latest GitHub release and run it.

There is no Python installation or manual model setup.

### GPU behaviour

PhotoEditor detects the available PyTorch backend automatically:

- NVIDIA CUDA GPU: use CUDA acceleration when available.
- No compatible NVIDIA GPU: use CPU automatically.

### Built-in model

The AI executable contains the YOLO11n segmentation model. On first AI use, PhotoEditor places a copy in:

`%USERPROFILE%\\.photoeditor\\ai\\models`

This means subsequent launches do not need to unpack the model again.

### AI model cache

Optional larger AI models are kept in the same PhotoEditor AI cache rather than being forced into the main executable. This keeps the consumer download much smaller and makes model updates independent from the application.

### Troubleshooting

If Windows security software blocks the application, use the normal Windows security review flow and only allow the executable if you trust the source.

If an NVIDIA GPU is not available, AI features continue through CPU fallback; processing will simply be slower.

from __future__ import annotations

from dataclasses import dataclass
import importlib.util


@dataclass(frozen=True)
class RuntimeInfo:
    torch: bool
    cuda: bool
    gpu_name: str
    ultralytics: bool
    transformers: bool
    embeddings: bool


def runtime_info(probe_cuda: bool = False) -> RuntimeInfo:
    """Inspect installed packages quickly; only import PyTorch when CUDA is needed."""
    torch_ok = importlib.util.find_spec("torch") is not None
    cuda = False
    name = ""
    if torch_ok and probe_cuda:
        try:
            import torch
            cuda = bool(torch.cuda.is_available())
            if cuda:
                name = str(torch.cuda.get_device_name(0))
        except Exception:
            # CPU remains a supported fallback if CUDA initialisation fails.
            cuda = False
            name = ""
    return RuntimeInfo(
        torch_ok,
        cuda,
        name,
        importlib.util.find_spec("ultralytics") is not None,
        importlib.util.find_spec("transformers") is not None,
        importlib.util.find_spec("sentence_transformers") is not None,
    )


def device() -> str:
    info = runtime_info(probe_cuda=True)
    return "cuda" if info.cuda else "cpu"

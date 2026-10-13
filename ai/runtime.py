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

def runtime_info() -> RuntimeInfo:
    torch_ok = importlib.util.find_spec("torch") is not None
    cuda = False
    name = ""
    if torch_ok:
        try:
            import torch
            cuda = bool(torch.cuda.is_available())
            if cuda:
                name = str(torch.cuda.get_device_name(0))
        except Exception:
            # Missing drivers or incompatible CUDA must not break the editor.
            cuda, name = False, ""
    try:
        transformers_ok = importlib.util.find_spec("transformers") is not None
    except (ImportError, ValueError):
        transformers_ok = False
    try:
        embeddings_ok = importlib.util.find_spec("sentence_transformers") is not None
    except (ImportError, ValueError):
        embeddings_ok = False
    return RuntimeInfo(torch_ok, cuda, name, False, transformers_ok, embeddings_ok)

def device() -> str:
    return "cuda" if runtime_info().cuda else "cpu"

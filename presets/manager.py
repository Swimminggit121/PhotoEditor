from __future__ import annotations
import json
from pathlib import Path
from core.adjustment_stack import Adjustments
PRESET_DIR=Path.home()/".photoeditor"/"presets"
def save_preset(adjustments,name,path=None):
    target=Path(path) if path else PRESET_DIR/(name.replace("/","_")+".json");target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(adjustments.to_dict(),indent=2),encoding="utf-8");return target
def load_preset(path):return Adjustments.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
def list_presets():
    PRESET_DIR.mkdir(parents=True,exist_ok=True);return sorted(PRESET_DIR.glob("*.json"))

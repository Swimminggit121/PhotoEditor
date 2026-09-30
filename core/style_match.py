from __future__ import annotations

from copy import deepcopy

from core.adjustment_stack import Adjustments
from core.auto_grade import auto_edit


STYLE_FIELDS = (
    "contrast", "highlights", "shadows", "whites", "blacks",
    "temperature", "tint", "saturation", "vibrance",
    "texture", "clarity", "dehaze", "sharpening", "noise_reduction",
    "grain", "vignette", "hsl", "curves_master", "curves_red",
    "curves_green", "curves_blue", "grading_shadows",
    "grading_midtones", "grading_highlights", "grading_global",
    "grading_blending", "grading_balance",
)


def build_style_profile(adjustments: Adjustments) -> dict:
    """Return a portable style profile containing grading controls only."""
    data = adjustments.to_dict()
    return {field: deepcopy(data[field]) for field in STYLE_FIELDS if field in data}


def apply_style_profile(image, profile: dict, strength: float = 0.75) -> Adjustments:
    """Auto-edit an image, then blend the saved grading style over it."""
    result = auto_edit(image)
    strength = max(0.0, min(1.0, float(strength)))

    for field in STYLE_FIELDS:
        if field not in profile:
            continue
        target = profile[field]
        current = getattr(result, field)

        if isinstance(target, (int, float)) and isinstance(current, (int, float)):
            setattr(result, field, current * (1.0 - strength) + float(target) * strength)
        elif isinstance(target, dict):
            if field == "hsl":
                merged = deepcopy(current)
                for channel, values in target.items():
                    if channel not in merged:
                        merged[channel] = deepcopy(values)
                        continue
                    for key, value in values.items():
                        merged[channel][key] = (
                            merged[channel].get(key, 0.0) * (1.0 - strength)
                            + float(value) * strength
                        )
                setattr(result, field, merged)
            else:
                merged = deepcopy(current)
                for key, value in target.items():
                    merged[key] = (
                        float(merged.get(key, 0.0)) * (1.0 - strength)
                        + float(value) * strength
                    )
                setattr(result, field, merged)
        elif isinstance(target, list):
            setattr(result, field, deepcopy(target))

    return result

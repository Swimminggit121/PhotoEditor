import numpy as np


def colour_from_hsl(
    hue,
    saturation,
    luminance=0.0
):
    angle = np.radians(
        hue
    )

    colour = np.array(
        [
            np.cos(angle),
            np.cos(
                angle
                - 2.094395
            ),
            np.cos(
                angle
                + 2.094395
            ),
        ],
        dtype=np.float32
    )

    colour -= colour.min()

    maximum = colour.max()

    if maximum > 0:
        colour /= maximum

    colour = (
        colour
        * (saturation / 100.0)
    )

    colour += (
        luminance / 100.0
    )

    return colour


def apply_colour_grade(
    image,
    shadows,
    midtones,
    highlights,
    global_grade,
    blending,
    balance
):
    result = image.copy()

    luminance = (
        result[..., 0] * 0.2126
        + result[..., 1] * 0.7152
        + result[..., 2] * 0.0722
    )

    shadow_weight = np.clip(
        (0.5 - luminance) * 2.0,
        0.0,
        1.0
    )

    highlight_weight = np.clip(
        (luminance - 0.5) * 2.0,
        0.0,
        1.0
    )

    midtone_weight = (
        1.0
        - np.abs(
            luminance - 0.5
        ) * 2.0
    )

    midtone_weight = np.clip(
        midtone_weight,
        0.0,
        1.0
    )

    blend = np.clip(
        blending / 100.0,
        0.0,
        1.0
    )

    balance_value = (
        balance / 100.0
    )

    shadow_weight *= (
        1.0
        - balance_value * 0.5
    )

    highlight_weight *= (
        1.0
        + balance_value * 0.5
    )

    shadow_colour = colour_from_hsl(
        shadows["hue"],
        shadows["saturation"],
        shadows["luminance"]
    )

    midtone_colour = colour_from_hsl(
        midtones["hue"],
        midtones["saturation"],
        midtones["luminance"]
    )

    highlight_colour = colour_from_hsl(
        highlights["hue"],
        highlights["saturation"],
        highlights["luminance"]
    )

    global_colour = colour_from_hsl(
        global_grade["hue"],
        global_grade["saturation"],
        global_grade["luminance"]
    )

    result += (
        shadow_weight[..., None]
        * shadow_colour
        * 0.15
    )

    result += (
        midtone_weight[..., None]
        * midtone_colour
        * 0.15
    )

    result += (
        highlight_weight[..., None]
        * highlight_colour
        * 0.15
    )

    result += (
        global_colour
        * 0.05
    )

    result = (
        image
        * (1.0 - blend)
        + result
        * blend
    )

    return np.clip(
        result,
        0.0,
        1.0
    )
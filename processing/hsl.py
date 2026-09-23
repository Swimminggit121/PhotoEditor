import colorsys
import numpy as np


CHANNELS = [
    "red",
    "orange",
    "yellow",
    "green",
    "aqua",
    "blue",
    "purple",
    "magenta",
]


CHANNEL_HUES = {
    "red": 0.0,
    "orange": 30.0,
    "yellow": 60.0,
    "green": 120.0,
    "aqua": 180.0,
    "blue": 240.0,
    "purple": 270.0,
    "magenta": 330.0,
}


def hue_distance(a, b):
    distance = np.abs(a - b)
    return np.minimum(
        distance,
        360.0 - distance
    )


def channel_weight(hue, centre, width=30.0):
    distance = hue_distance(
        hue,
        centre
    )

    weight = 1.0 - (
        distance / width
    )

    return np.clip(
        weight,
        0.0,
        1.0
    )


def rgb_to_hsv_array(image):
    maximum = np.max(
        image,
        axis=-1
    )

    minimum = np.min(
        image,
        axis=-1
    )

    delta = maximum - minimum

    value = maximum

    saturation = np.zeros_like(
        maximum
    )

    non_zero = maximum != 0

    saturation[non_zero] = (
        delta[non_zero]
        / maximum[non_zero]
    )

    hue = np.zeros_like(
        maximum
    )

    mask = delta != 0

    red = image[..., 0]
    green = image[..., 1]
    blue = image[..., 2]

    red_mask = (
        mask
        & (maximum == red)
    )

    green_mask = (
        mask
        & (maximum == green)
    )

    blue_mask = (
        mask
        & (maximum == blue)
    )

    hue[red_mask] = (
        60.0
        * (
            (green[red_mask] - blue[red_mask])
            / delta[red_mask]
        )
    )

    hue[green_mask] = (
        60.0
        * (
            (blue[green_mask] - red[green_mask])
            / delta[green_mask]
        )
        + 120.0
    )

    hue[blue_mask] = (
        60.0
        * (
            (red[blue_mask] - green[blue_mask])
            / delta[blue_mask]
        )
        + 240.0
    )

    hue %= 360.0

    return hue, saturation, value


def hsv_to_rgb_array(hue, saturation, value):
    h = hue / 60.0

    c = value * saturation

    x = c * (
        1.0
        - np.abs(
            (h % 2.0) - 1.0
        )
    )

    m = value - c

    r = np.zeros_like(hue)
    g = np.zeros_like(hue)
    b = np.zeros_like(hue)

    mask = (
        (h >= 0)
        & (h < 1)
    )

    r[mask] = c[mask]
    g[mask] = x[mask]

    mask = (
        (h >= 1)
        & (h < 2)
    )

    r[mask] = x[mask]
    g[mask] = c[mask]

    mask = (
        (h >= 2)
        & (h < 3)
    )

    g[mask] = c[mask]
    b[mask] = x[mask]

    mask = (
        (h >= 3)
        & (h < 4)
    )

    g[mask] = x[mask]
    b[mask] = c[mask]

    mask = (
        (h >= 4)
        & (h < 5)
    )

    r[mask] = x[mask]
    b[mask] = c[mask]

    mask = (
        (h >= 5)
        & (h < 6)
    )

    r[mask] = c[mask]
    b[mask] = x[mask]

    r += m
    g += m
    b += m

    return np.stack(
        [r, g, b],
        axis=-1
    )


def apply_hsl(image, hsl):
    if not hsl:
        return image

    hue, saturation, value = (
        rgb_to_hsv_array(image)
    )

    original_hue = hue.copy()

    for channel in CHANNELS:
        settings = hsl.get(
            channel,
            {}
        )

        hue_shift = settings.get(
            "hue",
            0.0
        )

        saturation_shift = settings.get(
            "saturation",
            0.0
        )

        luminance_shift = settings.get(
            "luminance",
            0.0
        )

        centre = CHANNEL_HUES[
            channel
        ]

        weight = channel_weight(
            original_hue,
            centre,
            30.0
        )

        hue += (
            weight
            * hue_shift
        )

        saturation += (
            weight
            * saturation_shift
            / 100.0
        )

        value += (
            weight
            * luminance_shift
            / 100.0
        )

    hue %= 360.0

    saturation = np.clip(
        saturation,
        0.0,
        1.0
    )

    value = np.clip(
        value,
        0.0,
        1.0
    )

    return np.clip(
        hsv_to_rgb_array(
            hue,
            saturation,
            value
        ),
        0.0,
        1.0
    )
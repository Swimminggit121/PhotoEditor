import cv2
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
    hsv = cv2.cvtColor(np.ascontiguousarray(image, dtype=np.float32), cv2.COLOR_RGB2HSV)
    return hsv[..., 0], hsv[..., 1], hsv[..., 2]


def hsv_to_rgb_array(hue, saturation, value):
    hsv = np.stack((hue, saturation, value), axis=-1).astype(np.float32, copy=False)
    return cv2.cvtColor(np.ascontiguousarray(hsv), cv2.COLOR_HSV2RGB)


def apply_hsl(image, hsl):
    if not hsl:
        return image

    hue, saturation, value = (
        rgb_to_hsv_array(image)
    )

    hue_adjustments = np.zeros(360, dtype=np.float32)
    saturation_adjustments = np.zeros(360, dtype=np.float32)
    value_adjustments = np.zeros(360, dtype=np.float32)
    sample_hues = np.arange(360, dtype=np.float32)
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

        if not (hue_shift or saturation_shift or luminance_shift):
            continue

        weight = channel_weight(sample_hues, CHANNEL_HUES[channel], 30.0)
        hue_adjustments += weight * hue_shift
        saturation_adjustments += weight * saturation_shift / 100.0
        value_adjustments += weight * luminance_shift / 100.0

    hue_floor = np.floor(hue)
    hue_low = hue_floor.astype(np.int32) % 360
    hue_high = (hue_low + 1) % 360
    hue_fraction = hue - hue_floor
    hue += (
        hue_adjustments[hue_low] * (1.0 - hue_fraction)
        + hue_adjustments[hue_high] * hue_fraction
    )
    saturation += (
        saturation_adjustments[hue_low] * (1.0 - hue_fraction)
        + saturation_adjustments[hue_high] * hue_fraction
    )
    value += (
        value_adjustments[hue_low] * (1.0 - hue_fraction)
        + value_adjustments[hue_high] * hue_fraction
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
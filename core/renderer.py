import numpy as np
from PIL import Image

from core.adjustment_stack import Adjustments


def _clip(array):
    return np.clip(array, 0.0, 1.0)


def apply_exposure(image, value):
    multiplier = 2.0 ** value
    return _clip(image * multiplier)


def apply_contrast(image, value):
    factor = (100.0 + value) / 100.0
    return _clip((image - 0.5) * factor + 0.5)


def apply_highlights_shadows(image, highlights, shadows):
    luminance = (
        image[..., 0] * 0.2126
        + image[..., 1] * 0.7152
        + image[..., 2] * 0.0722
    )

    highlight_mask = np.clip(
        (luminance - 0.5) * 2.0,
        0.0,
        1.0
    )[..., None]

    shadow_mask = np.clip(
        (0.5 - luminance) * 2.0,
        0.0,
        1.0
    )[..., None]

    image = image + (
        highlight_mask * highlights / 100.0 * 0.35
    )

    image = image + (
        shadow_mask * shadows / 100.0 * 0.35
    )

    return _clip(image)


def apply_whites_blacks(image, whites, blacks):
    image = image + whites / 100.0 * 0.25
    image = image + blacks / 100.0 * 0.25

    return _clip(image)


def apply_temperature(image, value):
    amount = value / 100.0

    red = image[..., 0]
    green = image[..., 1]
    blue = image[..., 2]

    red = red + amount * 0.12
    blue = blue - amount * 0.12

    return _clip(
        np.stack(
            [red, green, blue],
            axis=-1
        )
    )


def apply_tint(image, value):
    amount = value / 100.0

    red = image[..., 0]
    green = image[..., 1]
    blue = image[..., 2]

    red = red + amount * 0.05
    green = green - amount * 0.10
    blue = blue + amount * 0.05

    return _clip(
        np.stack(
            [red, green, blue],
            axis=-1
        )
    )


def apply_saturation(image, value):
    saturation = 1.0 + value / 100.0

    luminance = (
        image[..., 0] * 0.2126
        + image[..., 1] * 0.7152
        + image[..., 2] * 0.0722
    )

    luminance = luminance[..., None]

    return _clip(
        luminance
        + (image - luminance) * saturation
    )


def apply_vibrance(image, value):
    amount = value / 100.0

    max_channel = np.max(image, axis=-1)
    min_channel = np.min(image, axis=-1)

    saturation = max_channel - min_channel

    boost = (1.0 - saturation)[..., None]

    return _clip(
        image + (image - image.mean(axis=-1, keepdims=True))
        * boost
        * amount
        * 0.7
    )


def render_image(image, adjustments: Adjustments):
    array = np.asarray(image).astype(np.float32) / 255.0

    array = apply_exposure(
        array,
        adjustments.exposure
    )

    array = apply_contrast(
        array,
        adjustments.contrast
    )

    array = apply_highlights_shadows(
        array,
        adjustments.highlights,
        adjustments.shadows
    )

    array = apply_whites_blacks(
        array,
        adjustments.whites,
        adjustments.blacks
    )

    array = apply_temperature(
        array,
        adjustments.temperature
    )

    array = apply_tint(
        array,
        adjustments.tint
    )

    array = apply_saturation(
        array,
        adjustments.saturation
    )

    array = apply_vibrance(
        array,
        adjustments.vibrance
    )

    array = (_clip(array) * 255.0).astype(np.uint8)

    return Image.fromarray(array, "RGB")
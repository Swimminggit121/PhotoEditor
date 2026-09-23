import numpy as np


DEFAULT_CURVE = [
    (0.0, 0.0),
    (1.0, 1.0),
]


def interpolate_curve(points, values):
    points = sorted(
        points,
        key=lambda point: point[0]
    )

    xs = np.array(
        [point[0] for point in points],
        dtype=np.float32
    )

    ys = np.array(
        [point[1] for point in points],
        dtype=np.float32
    )

    return np.interp(
        values,
        xs,
        ys
    )


def apply_curve_channel(
    channel,
    points
):
    if not points:
        return channel

    lookup_values = np.linspace(
        0.0,
        1.0,
        4096
    )

    lookup = interpolate_curve(
        points,
        lookup_values
    )

    indices = np.clip(
        (
            channel
            * (len(lookup) - 1)
        ).astype(np.int32),
        0,
        len(lookup) - 1
    )

    return lookup[indices]


def apply_curves(
    image,
    master,
    red,
    green,
    blue
):
    result = image.copy()

    if master:
        result[..., 0] = apply_curve_channel(
            result[..., 0],
            master
        )

        result[..., 1] = apply_curve_channel(
            result[..., 1],
            master
        )

        result[..., 2] = apply_curve_channel(
            result[..., 2],
            master
        )

    if red:
        result[..., 0] = apply_curve_channel(
            result[..., 0],
            red
        )

    if green:
        result[..., 1] = apply_curve_channel(
            result[..., 1],
            green
        )

    if blue:
        result[..., 2] = apply_curve_channel(
            result[..., 2],
            blue
        )

    return np.clip(
        result,
        0.0,
        1.0
    )
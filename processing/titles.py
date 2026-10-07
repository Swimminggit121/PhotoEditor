from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def render_title(text: str, width: int, height: int) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    lines = []
    columns = max(16, min(48, width // 24))
    for paragraph in text.splitlines() or [text]:
        lines.extend(textwrap.wrap(paragraph, columns) or [""])

    font_size = max(28, min(76, width // 18))
    candidates = (
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    font = ImageFont.load_default()
    for candidate in candidates:
        if candidate.is_file():
            try:
                font = ImageFont.truetype(str(candidate), font_size)
                break
            except OSError:
                continue

    draw = ImageDraw.Draw(canvas)
    spacing = max(8, font_size // 4)
    bounds = draw.multiline_textbbox((0, 0), "\n".join(lines), font=font, align="center", spacing=spacing, stroke_width=1)
    text_width = bounds[2] - bounds[0]
    text_height = bounds[3] - bounds[1]
    padding_x = max(28, width // 32)
    padding_y = max(18, height // 36)
    box_width = min(width - 32, text_width + padding_x * 2)
    box_height = text_height + padding_y * 2
    left = (width - box_width) // 2
    top = max(16, height - box_height - max(45, height // 12))
    draw.rounded_rectangle((left, top, left + box_width, top + box_height), radius=max(8, font_size // 4), fill=(0, 0, 0, 174))
    draw.multiline_text(
        (width // 2, top + padding_y),
        "\n".join(lines),
        font=font,
        fill=(255, 255, 255, 255),
        anchor="ma",
        align="center",
        spacing=spacing,
        stroke_width=1,
        stroke_fill=(0, 0, 0, 100),
    )
    return canvas

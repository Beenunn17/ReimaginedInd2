"""Image manipulation utilities.

This module wraps common operations on images using Pillow, such as
resizing and overlaying text. These helpers are used by the API
endpoints when processing uploaded assets for the creative library.
"""

from __future__ import annotations

from io import BytesIO
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]


def _open_image(data: bytes) -> Image.Image:
    """Open raw image bytes with Pillow and convert to RGB."""
    img = Image.open(BytesIO(data))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def resize_image(data: bytes, max_size: int) -> bytes:
    """Resize an image so that its largest dimension equals `max_size`.

    Args:
        data: Raw image bytes.
        max_size: Maximum width/height for the output image.

    Returns:
        The resized image as JPEG bytes.
    """
    img = _open_image(data)
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def overlay_text(data: bytes, text: str, position: Tuple[int, int] | None = None) -> bytes:
    """Overlay a text string onto an image.

    By default the text is placed near the bottom-left corner. A custom
    position can be provided via the `position` argument. A basic Pillow
    font is used because no font files are available in this environment.

    Args:
        data: Raw image bytes.
        text: Text to overlay.
        position: (x, y) tuple specifying the top-left corner of the text.

    Returns:
        The modified image as JPEG bytes.
    """
    img = _open_image(data)
    draw = ImageDraw.Draw(img)
    # Use a default bitmap font
    try:
        font = ImageFont.truetype("arial.ttf", size=24)
    except Exception:
        font = ImageFont.load_default()
    # Determine text size
    text_width, text_height = draw.textsize(text, font=font)
    if position is None:
        x = max(10, (img.width - text_width) // 2)
        y = img.height - text_height - 10
    else:
        x, y = position
    # Draw semi-transparent rectangle behind text for readability
    margin = 4
    rect_coords = [x - margin, y - margin, x + text_width + margin, y + text_height + margin]
    draw.rectangle(rect_coords, fill=(0, 0, 0, 127))  # semi-transparent
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()
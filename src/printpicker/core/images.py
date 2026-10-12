"""Loading photos of any supported format as upright RGB Pillow images."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

# Archive photos can be very large (panoramas); they come from the user's own disk.
Image.MAX_IMAGE_PIXELS = None


class ImageLoadError(Exception):
    """A photo could not be read or decoded."""


def load_image(path: Path, max_size: int | None = None) -> Image.Image:
    """Load ``path`` as an RGB image with EXIF orientation applied.

    With ``max_size``, the result fits in a ``max_size`` × ``max_size`` box; decoding is
    accelerated where the format allows it (JPEG draft mode).
    """
    try:
        with Image.open(path) as img:
            if max_size is not None and img.format == "JPEG":
                # Decode at a reduced scale (1/2, 1/4, 1/8): much faster for thumbnails.
                img.draft("RGB", (max_size, max_size))
            img = ImageOps.exif_transpose(img)
            img = _to_rgb(img)
            if max_size is not None:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            img.load()
            return img
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ImageLoadError(f"{path}: {exc}") from exc


def _to_rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGB":
        return img
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        # Flatten transparency on white, like a print would.
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return img.convert("RGB")

"""Camera RAW decoding (CR2, NEF, ARW, DNG, ...) via rawpy / LibRaw."""

from __future__ import annotations

import io
from pathlib import Path

import rawpy
from PIL import Image, ImageOps

# LibRaw "flip" value -> Pillow transpose that makes the image upright.
_FLIP_TRANSPOSE = {
    3: Image.Transpose.ROTATE_180,
    5: Image.Transpose.ROTATE_90,  # 90° counter-clockwise
    6: Image.Transpose.ROTATE_270,  # 90° clockwise
}

_ORIENTATION_TAG = 0x0112


def load_raw(path: Path, max_size: int | None = None) -> Image.Image:
    """Decode a RAW file as an upright RGB image.

    For previews (``max_size`` given) the JPEG embedded by the camera is used when it is large
    enough: it is much faster than demosaicing. Full-size loads always develop the RAW data.
    """
    with rawpy.imread(str(path)) as raw:
        if max_size is not None:
            preview = _embedded_preview(raw)
            if preview is not None and max(preview.size) >= max_size:
                return preview
        rgb = raw.postprocess(use_camera_wb=True, half_size=max_size is not None, output_bps=8)
    # postprocess() already applies the orientation.
    return Image.fromarray(rgb)


def _embedded_preview(raw) -> Image.Image | None:
    try:
        thumb = raw.extract_thumb()
    except (rawpy.LibRawNoThumbnailError, rawpy.LibRawUnsupportedThumbnailError):
        return None
    if thumb.format == rawpy.ThumbFormat.JPEG:
        img = Image.open(io.BytesIO(thumb.data))
        has_orientation = img.getexif().get(_ORIENTATION_TAG, 1) != 1
        img = ImageOps.exif_transpose(img)
        if not has_orientation:
            transpose = _FLIP_TRANSPOSE.get(raw.sizes.flip)
            if transpose is not None:
                img = img.transpose(transpose)
    elif thumb.format == rawpy.ThumbFormat.BITMAP:
        img = Image.fromarray(thumb.data)
    else:
        return None
    return img.convert("RGB")

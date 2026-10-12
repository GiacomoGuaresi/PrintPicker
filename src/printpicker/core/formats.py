"""Supported file formats."""

JPEG_EXTENSIONS = frozenset({".jpg", ".jpeg"})
PNG_EXTENSIONS = frozenset({".png"})
HEIF_EXTENSIONS = frozenset({".heic", ".heif"})
TIFF_EXTENSIONS = frozenset({".tif", ".tiff"})
WEBP_EXTENSIONS = frozenset({".webp"})
RAW_EXTENSIONS = frozenset(
    {
        ".cr2",
        ".cr3",
        ".crw",
        ".nef",
        ".nrw",
        ".arw",
        ".srf",
        ".sr2",
        ".dng",
        ".orf",
        ".rw2",
        ".raf",
        ".pef",
        ".srw",
        ".3fr",
        ".erf",
        ".kdc",
        ".mrw",
        ".x3f",
    }
)

SUPPORTED_EXTENSIONS = (
    JPEG_EXTENSIONS
    | PNG_EXTENSIONS
    | HEIF_EXTENSIONS
    | TIFF_EXTENSIONS
    | WEBP_EXTENSIONS
    | RAW_EXTENSIONS
)

# Formats copied unchanged on export; everything else is converted to JPG.
PASSTHROUGH_EXTENSIONS = JPEG_EXTENSIONS | PNG_EXTENSIONS


def extension(name: str) -> str:
    """Lower-case extension of a file name, including the dot."""
    dot = name.rfind(".")
    return name[dot:].lower() if dot > 0 else ""


def is_supported(name: str) -> bool:
    return extension(name) in SUPPORTED_EXTENSIONS


def is_raw(name: str) -> bool:
    return extension(name) in RAW_EXTENSIONS


def is_heif(name: str) -> bool:
    return extension(name) in HEIF_EXTENSIONS

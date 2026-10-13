"""Download the image embedding model used to group similar photos.

    uv run python scripts/fetch_model.py

DINOv2 ViT-S/14 (Meta, Apache 2.0) as ONNX fp16 from onnx-community, pinned to a revision
and checked against its SHA-256. It is git-ignored (~44 MB) and bundled into the app by
PyInstaller. Without it PrintPicker still works, grouping with the perceptual hash only.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from printpicker.core.embedding import MODEL_PATH  # noqa: E402

REVISION = "8b1f705a3a7f6f062f6bdd21986c1583d3ef105d"
URL = f"https://huggingface.co/onnx-community/dinov2-small/resolve/{REVISION}/onnx/model_fp16.onnx"
SHA256 = "16845e153bbaf3fd1ef8a2154c454940f901f6fe8a80dd4c6c319eaecdb4d2ee"
SIZE = 44_420_939
ATTEMPTS = 10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if MODEL_PATH.exists() and sha256(MODEL_PATH) == SHA256:
        print(f"{MODEL_PATH} is up to date")
        return 0
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    partial = MODEL_PATH.with_suffix(".part")
    partial.unlink(missing_ok=True)
    print(f"downloading {URL}")
    # Slow connections drop long downloads: resume where it stopped.
    for _ in range(ATTEMPTS):
        done = partial.stat().st_size if partial.exists() else 0
        if done == SIZE:
            break
        request = urllib.request.Request(URL, headers={"Range": f"bytes={done}-"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response, partial.open("ab") as out:
                while chunk := response.read(1 << 20):
                    out.write(chunk)
        except OSError as exc:
            print(f"  interrupted at {done} bytes: {exc}", file=sys.stderr)
    if not partial.exists() or sha256(partial) != SHA256:
        partial.unlink(missing_ok=True)
        print("checksum mismatch, model discarded", file=sys.stderr)
        return 1
    partial.replace(MODEL_PATH)
    print(f"saved {MODEL_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

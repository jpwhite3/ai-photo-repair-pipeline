"""Persist restoration outputs to a timestamped directory.

Each run writes: the restored image, a copy of the original, ``analysis.json`` and
``verification.json``. Slug/suffix helpers are adapted from the reference repo.
"""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from photo_repair.state import RestorationState

logger = logging.getLogger(__name__)


def _slugify(text: str, max_length: int = 60) -> str:
    """Create a filesystem-safe, truncated slug from text."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if not text:
        return "photo"
    if len(text) <= max_length:
        return text
    cut = text.rfind("-", 0, max_length)
    if cut == -1:
        cut = max_length
    return text[:cut] or text[:max_length]


def _unique_suffix(source: str) -> str:
    """Return a short deterministic suffix from a hash of the source text."""
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()  # nosec - non-crypto use
    return digest[:8]


def _ext_for(mime_type: str, fallback: str = ".png") -> str:
    """Map a mime type to a file extension."""
    return mimetypes.guess_extension(mime_type) or fallback


def save_restoration_outputs(state: RestorationState, base_dir: str = "restored_photos") -> str:
    """Write a single restoration's artifacts to a timestamped directory.

    Returns the absolute path to the directory created.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = Path(state.input_path).stem or "photo"
    slug = _slugify(stem)
    suffix = _unique_suffix(f"{state.input_path}:{timestamp}")

    out_dir = Path(base_dir) / f"{slug}_{timestamp}_{suffix}"
    out_dir.mkdir(parents=True, exist_ok=True)

    ext = _ext_for(state.mime_type)
    try:
        # Copy of the original input
        (out_dir / f"original{ext}").write_bytes(state.image_bytes)
        # The restored result (if produced)
        if state.restored_bytes is not None:
            (out_dir / f"restored{ext}").write_bytes(state.restored_bytes)
        # Structured artifacts
        if state.analysis is not None:
            (out_dir / "analysis.json").write_text(
                json.dumps(state.analysis.model_dump(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        if state.verification is not None:
            (out_dir / "verification.json").write_text(
                json.dumps(state.verification.model_dump(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        if state.notes:
            (out_dir / "notes.txt").write_text("\n".join(state.notes), encoding="utf-8")
    except OSError as err:
        logger.exception("Failed to write one or more artifacts: %s", err)

    return str(out_dir.resolve())

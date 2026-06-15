"""Command-line interface for the photo restoration pipeline.

Usage:
    photo-repair path/to/photo.jpg            # restore a single image
    photo-repair path/to/folder/ --batch      # restore every image in a folder
    photo-repair photo.jpg --out ./results    # override the output directory
"""

from __future__ import annotations

import argparse
import logging
import mimetypes
import sys
from collections.abc import Callable
from pathlib import Path

from photo_repair.state import RestorationState

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}

# A runner takes (image_bytes, input_path, mime_type) and returns the final state.
RestoreFn = Callable[[bytes, str, str], RestorationState]


def resolve_inputs(path: str, batch: bool) -> list[Path]:
    """Resolve the CLI path argument into a list of image files to process."""
    p = Path(path)
    if batch:
        if not p.is_dir():
            return []
        return sorted(
            f for f in p.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        )
    if p.is_file():
        return [p]
    return []


def _mime_for(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "image/png"


def _build_default_runner(
    out_override: str | None, model_override: str | None = None, force: bool = False
) -> RestoreFn:
    """Build the real pipeline runner from settings (validates the API key)."""
    from photo_repair.config import get_settings
    from photo_repair.graph import restore_photo
    from photo_repair.image_client import ImageClient

    settings = get_settings()
    client = ImageClient.from_settings(settings, restore_model=model_override)
    base_dir = out_override or settings.output_dir
    max_attempts = settings.max_restore_attempts

    def runner(image_bytes: bytes, input_path: str, mime_type: str) -> RestorationState:
        return restore_photo(
            image_bytes=image_bytes,
            input_path=input_path,
            client=client,
            mime_type=mime_type,
            max_attempts=max_attempts,
            base_dir=base_dir,
            force=force,
        )

    return runner


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="photo-repair", description="Restore old or damaged photos with AI."
    )
    parser.add_argument("path", help="Path to an image, or a folder when using --batch.")
    parser.add_argument(
        "--batch", action="store_true", help="Treat PATH as a folder and restore every image in it."
    )
    parser.add_argument("--out", default=None, help="Output directory (overrides OUTPUT_DIR).")
    parser.add_argument(
        "--model",
        default=None,
        help="Restoration model id for this run (overrides RESTORE_IMAGE_MODEL).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreation of analysis and plan.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, restore_fn: RestoreFn | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args(argv)

    inputs = resolve_inputs(args.path, args.batch)
    if not inputs:
        target = "folder with images" if args.batch else "image file"
        print(f"error: no {target} found at '{args.path}'", file=sys.stderr)
        return 2

    if restore_fn is None:
        try:
            restore_fn = _build_default_runner(
                args.out, model_override=args.model, force=args.force
            )
        except Exception as err:  # noqa: BLE001 - surface config errors cleanly
            print(f"error: {err}", file=sys.stderr)
            print(
                "Set GOOGLE_API_KEY (https://aistudio.google.com/app/apikey) in your "
                "environment or a .env file.",
                file=sys.stderr,
            )
            return 1

    failures = 0
    for path in inputs:
        try:
            image_bytes = path.read_bytes()
            state = restore_fn(image_bytes, str(path), _mime_for(path))
            ok = state.verification is None or state.verification.passed
            status = "ok" if ok else "needs review"
            print(f"{path.name} -> {state.output_path} [{status}]")
        except Exception as err:  # noqa: BLE001 - keep processing the rest of the batch
            failures += 1
            logger.exception("Failed to restore %s: %s", path, err)
            print(f"error: failed to restore '{path}': {err}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

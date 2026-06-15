"""Tests for photo_repair.storage."""

import json
from pathlib import Path


def test_slugify_basic():
    from photo_repair.storage import _slugify

    assert _slugify("My Old Photo.JPG") == "my-old-photo-jpg"
    assert _slugify("") == "photo"


def test_unique_suffix_deterministic():
    from photo_repair.storage import _unique_suffix

    a = _unique_suffix("abc")
    b = _unique_suffix("abc")
    assert a == b
    assert len(a) == 8
    assert _unique_suffix("abc") != _unique_suffix("xyz")


def test_save_restoration_outputs_writes_all_artifacts(tmp_path):
    from photo_repair.state import RestorationAnalysis, RestorationState, VerificationResult
    from photo_repair.storage import save_restoration_outputs

    state = RestorationState(
        input_path="/somewhere/grandpa.jpg",
        image_bytes=b"ORIGINAL_BYTES",
        mime_type="image/jpeg",
        restored_bytes=b"RESTORED_BYTES",
        analysis=RestorationAnalysis(
            era="1940s",
            photographic_process="gelatin silver print",
            defects=["scratches"],
            is_black_and_white=True,
        ),
        verification=VerificationResult(
            composition_preserved=True,
            identity_preserved=True,
            clothing_preserved=True,
            environment_preserved=True,
            no_hallucinations_or_artifacts=True,
            text_and_signage_preserved=True,
            tonality_and_grain_preserved=True,
            quality_ok=True,
            issues=[],
        ),
    )

    out_dir = save_restoration_outputs(state, base_dir=str(tmp_path))
    out = Path(out_dir)

    assert out.exists() and out.is_dir()
    assert out.parent == tmp_path

    # Restored image + original copy
    restored = list(out.glob("restored.*"))
    original = list(out.glob("original.*"))
    assert restored and restored[0].read_bytes() == b"RESTORED_BYTES"
    assert original and original[0].read_bytes() == b"ORIGINAL_BYTES"

    # Structured JSON artifacts
    analysis = json.loads((out / "analysis.json").read_text())
    assert analysis["era"] == "1940s"
    verification = json.loads((out / "verification.json").read_text())
    assert verification["composition_preserved"] is True


def test_save_restoration_outputs_returns_unique_dirs(tmp_path):
    from photo_repair.state import RestorationState
    from photo_repair.storage import save_restoration_outputs

    s1 = RestorationState(input_path="a.jpg", image_bytes=b"a", restored_bytes=b"a")
    s2 = RestorationState(input_path="b.jpg", image_bytes=b"b", restored_bytes=b"b")
    d1 = save_restoration_outputs(s1, base_dir=str(tmp_path))
    d2 = save_restoration_outputs(s2, base_dir=str(tmp_path))
    assert d1 != d2

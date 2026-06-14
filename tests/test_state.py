"""Tests for photo_repair.state and photo_repair.prompts."""


def test_restoration_prompt_is_verbatim():
    """The user's restoration prompt must be stored EXACTLY, with no edits."""
    from photo_repair.prompts import RESTORATION_PROMPT

    expected = (
        "Restore this photo with period-accurate techniques, addressing any age-related "
        "issues it may have, such as blurring, damage, fading, scratches, tears, folds, "
        "worn-out areas, or being in black and white. First, analyze the image to identify "
        "the approximate era and original photographic process to ensure a historically "
        "accurate restoration. Make it look fresh and clear by gently sharpening soft edges "
        "and facial features without overdoing it, smoothing out grainy spots or noise if "
        "present, and reconstructing missing parts with realistic textures that match the "
        "original. If colors are faded or absent, bring them back naturally and vibrantly "
        "but true to the era's photographic technology without looking artificial; balance "
        "colors to match natural lighting, adjust brightness and contrast so everything pops "
        "nicely, and maintain original tonality. Add subtle details to objects or backgrounds "
        "that might have been lost, like fine lines in clothing, lifelike skin textures, or "
        "small elements in the scenery, while keeping the overall feel authentic, preserving "
        "natural grain patterns, and not changing the composition. Ensure the whole image is "
        "balanced, with no harsh shadows or washed-out areas, remove technical defects while "
        "respecting the nostalgic charm and exposure qualities of the time. Finally, upscale "
        "it to a higher resolution like Full HD 4k for better clarity, outputting in a "
        "photo-realistic style that looks like a professionally restored or recent "
        "high-quality photo. Do not change the composition of the image or the appearance of "
        "any person within it."
    )
    assert RESTORATION_PROMPT == expected


def test_analysis_and_verify_prompts_exist():
    from photo_repair import prompts

    assert isinstance(prompts.ANALYSIS_PROMPT, str) and prompts.ANALYSIS_PROMPT
    assert isinstance(prompts.VERIFY_PROMPT, str) and prompts.VERIFY_PROMPT


def test_restoration_analysis_model():
    from photo_repair.state import RestorationAnalysis

    analysis = RestorationAnalysis(
        era="1950s",
        photographic_process="black-and-white gelatin silver print",
        defects=["scratches", "fading"],
        is_black_and_white=True,
        notes="moderate damage",
    )
    assert analysis.defects == ["scratches", "fading"]
    assert analysis.is_black_and_white is True


def test_verification_result_model():
    from photo_repair.state import VerificationResult

    v = VerificationResult(
        composition_preserved=True,
        identity_preserved=True,
        quality_ok=True,
        issues=[],
    )
    assert v.passed is True

    failing = VerificationResult(
        composition_preserved=False,
        identity_preserved=True,
        quality_ok=True,
        issues=["crop changed"],
    )
    assert failing.passed is False


def test_restoration_state_defaults():
    from photo_repair.state import RestorationState

    state = RestorationState(input_path="/tmp/photo.jpg", image_bytes=b"abc")
    assert state.input_path == "/tmp/photo.jpg"
    assert state.attempts == 0
    assert state.analysis is None
    assert state.restored_bytes is None
    assert state.notes == []
    assert state.current_step == "initialized"

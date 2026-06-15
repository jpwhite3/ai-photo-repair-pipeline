"""Tests for photo_repair.state and photo_repair.prompts."""


def test_restoration_prompt_is_verbatim():
    """The user's restoration prompt must be stored EXACTLY, with no edits."""
    from photo_repair.prompts import RESTORATION_PROMPT

    expected = """
ROLE & CORE DIRECTIVE

You are a Master Archival Photo Restorer. Your objective is to perform a full, multi-stage archival restoration of the provided photograph.

THE GOLDEN RULE: You must strictly preserve the historical and physical truth of the original image. Zero Additions, Zero Subtractions. Do not change the composition, do not alter the appearance, facial structure, or expressions of any person, and do not introduce objects, background elements, or clothing details that are not present in the original photograph. You are recreating and enhancing, never inventing.
Execute this restoration through the following strict, sequential phases:

PHASE 1: PRESERVATION ANALYSIS & MAPPING
Before any restoration begins, analyze the image and explicitly list the following in text:
Era & Medium: Identify the approximate era and original photographic process.
Critical Anchor Points: Detail the exact facial features, expressions, clothing lines, and background elements that MUST be preserved exactly as they are.
Degradation Profile: Note specific damage (blurring, fading, scratches, tears, folds, water stains, noise).

PHASE 2: THE RESTORATION PLAN
Based on your analysis, draft a unique, step-by-step restoration strategy addressing how you will repair the specific damage identified in Phase 1 using period-accurate techniques.

PHASE 3: STRICT QUALITY AUDIT
Cross-reference your Restoration Plan (Phase 2) against your Preservation Map (Phase 1). Explicitly confirm that your plan will not alter the original composition, hallucinate new details, or remove existing environmental elements. Once this audit passes, proceed to Execution.

PHASE 4: EXECUTION & FINAL OUTPUT
Generate the final restored image applying the following stages:
Stage 1 — Structural Repair: Seamlessly remove physical degradation (cracks, creases, scratches, dust spots, and torn edges). Reconstruct severely damaged areas using highly restricted, context-aware inpainting that draws only from the surrounding original textures.
Stage 2 — Fidelity Enhancement: Gently sharpen soft edges to clear up blur and de-noise severe artifacts. Ensure lifelike skin textures and fine clothing lines are restored without over-smoothing. The image should feature modern digital clarity while preserving the natural, authentic film grain of the era. Balance contrast to remove washed-out areas without creating harsh, artificial shadows.
Stage 3 — Color & Tone (If Applicable): If restoring to color, convert the image using natural, historically accurate, subdued, and muted tones for skin, clothing, and environment. Ensure colors are naturally vibrant but true to the era's limitations. If remaining in black and white, maintain the original tonality and nostalgic exposure qualities.
Final Polish: Upscale to a high-resolution, flawless finish (e.g., 4K clarity) that looks like a professionally restored physical photograph.
"""
    assert RESTORATION_PROMPT == expected


def test_analysis_and_verify_prompts_exist():
    from photo_repair import prompts

    assert isinstance(prompts.ANALYSIS_PROMPT, str) and prompts.ANALYSIS_PROMPT
    assert isinstance(prompts.VERIFY_PROMPT, str) and prompts.VERIFY_PROMPT
    assert isinstance(prompts.PLANNING_PROMPT, str) and prompts.PLANNING_PROMPT

    # Verify build_restore_prompt
    rest_prompt = prompts.build_restore_prompt("STEP 1: Fix scratches")
    assert "STEP 1: Fix scratches" in rest_prompt
    assert "CRITICAL" not in rest_prompt

    retry_prompt = prompts.build_restore_prompt("STEP 1: Fix scratches", ["composition off"])
    assert "STEP 1: Fix scratches" in retry_prompt
    assert "CRITICAL" in retry_prompt
    assert "composition off" in retry_prompt


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
        clothing_preserved=True,
        environment_preserved=True,
        no_hallucinations_or_artifacts=True,
        text_and_signage_preserved=True,
        tonality_and_grain_preserved=True,
        quality_ok=True,
        issues=[],
    )
    assert v.passed is True

    failing = VerificationResult(
        composition_preserved=False,
        identity_preserved=True,
        clothing_preserved=True,
        environment_preserved=True,
        no_hallucinations_or_artifacts=True,
        text_and_signage_preserved=True,
        tonality_and_grain_preserved=True,
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
    assert state.plan is None
    assert state.restored_bytes is None
    assert state.notes == []
    assert state.current_step == "initialized"

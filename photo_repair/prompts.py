"""Prompt text for the restoration pipeline.

``RESTORATION_PROMPT`` is the user's prompt, stored VERBATIM. It is the single
restoration instruction sent to the image model — do not edit or parameterize it.
"""

# The canonical restoration instruction, exactly as provided by the user.
RESTORATION_PROMPT = """
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

# Vision prompt to characterise the photo before restoration. Output is parsed into a
# RestorationAnalysis (the SDK is given the schema via response_schema).
ANALYSIS_PROMPT = (
    "You are a photo-restoration archivist. Examine this photograph and report on its "
    "condition for an upcoming restoration. Identify the approximate era it was taken, "
    "the likely original photographic process (e.g. daguerreotype, gelatin silver print, "
    "color negative), whether it is black and white, and every visible age-related defect "
    "(blurring, fading, scratches, tears, folds, stains, noise, missing areas). Be concise "
    "and factual."
)

# Planning prompt to generate a step-by-step restoration strategy.
PLANNING_PROMPT = (
    "You are a Master Archival Photo Restorer. Analyze this photograph and its condition report:\n"
    "Era: {era}, Process: {process}, Defects: {defects}, Black & White: {is_bw}.\n"
    "Colorization Directive: {colorize_directive}\n\n"
    "Draft a step-by-step restoration plan to repair this photograph.\n"
    "Your plan must address how to repair each defect (e.g. scratch removal, de-noising) "
    "using period-accurate techniques. Detail what elements must be preserved exactly (facial structures, "
    "clothing styles, background scenery) and define the final target aesthetic (e.g., preserving authentic "
    "film grain, avoiding an airbrushed/plastic look). Output a detailed plan in markdown format."
)

# Helper to construct a dynamic prompt for the image-editing model.
def build_restore_prompt(plan: str, issues: list[str] | None = None) -> str:
    prompt = (
        "Restore this photograph by executing the following restoration plan exactly. "
        "Do not change the composition, people's identities, or add new elements.\n\n"
        f"RESTORATION PLAN:\n{plan}"
    )
    if issues:
        bullet_points = "\n".join(f"- {issue}" for issue in issues)
        prompt += (
            "\n\nCRITICAL: A previous restoration attempt failed verification with these issues. "
            "You MUST correct these specific errors in this run:\n"
            f"{bullet_points}"
        )
    return prompt

# Vision prompt to verify the restored image against the original's hard constraints.
VERIFY_PROMPT = (
    "You are reviewing a restored photograph (second image) against its original (first image).\n"
    "Examine both images and check the following criteria strictly. If a criterion is violated, "
    "set its field to false and list the reason in 'issues':\n\n"
    "1. composition_preserved: True if framing, crop, and layout of subjects are identical.\n"
    "2. identity_preserved: True if facial structure, features, and expressions of all people match.\n"
    "3. clothing_preserved: True if clothing style, details, fabrics, and patterns match.\n"
    "4. environment_preserved: True if scenery, background details, lighting, and objects match.\n"
    "5. no_hallucinations_or_artifacts: True if free of extra limbs, floating artifacts, or distortions.\n"
    "6. text_and_signage_preserved: True if text/writing is legible and matches the original.\n"
    "7. tonality_and_grain_preserved: True if authentic film grain and exposure contrast are kept (no plastic/over-smoothed look).\n"
    "8. quality_ok: True if overall restoration is clean, professional, and high quality. "
    "Note: If the original is black and white but the restored is colorized, verify that the colorization "
    "is natural, realistic, and period-appropriate (no modern neon shades, cartoonish skin tones, or bleeding colors).\n\n"
    "Identify any issues carefully."
)

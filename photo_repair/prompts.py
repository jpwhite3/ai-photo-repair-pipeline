"""Prompt text for the restoration pipeline.

``RESTORATION_PROMPT`` is the user's prompt, stored VERBATIM. It is the single
restoration instruction sent to the image model — do not edit or parameterize it.
"""

# The canonical restoration instruction, exactly as provided by the user.
RESTORATION_PROMPT = (
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

# Vision prompt to verify the restored image against the original's hard constraints.
VERIFY_PROMPT = (
    "You are reviewing a restored photograph against its original. Confirm that the "
    "restoration did NOT change the composition (framing, crop, layout of subjects) and "
    "did NOT change the appearance or identity of any person in the image. Also judge "
    "whether the technical quality is acceptable (sharp, balanced exposure, natural color, "
    "free of obvious artifacts). List any issues you find. The first image is the original; "
    "the second image is the restored result."
)

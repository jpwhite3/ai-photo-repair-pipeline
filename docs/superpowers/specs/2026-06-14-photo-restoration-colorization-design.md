# Design Document: Automatic Colorization of Black & White Photos

**Date:** 2026-06-14  
**Status:** Approved  
**Author:** Antigravity AI Coding Assistant  

---

## 1. Overview & Objectives

By default, black and white photos processed by the restoration pipeline should be automatically colorized, unless a `--no-colorize` CLI flag is explicitly passed.
To implement this:
1. We add a `no_colorize` boolean flag to the pipeline state.
2. If the input image is black and white, and `no_colorize` is False, the `plan` step will explicitly instruct the restoration model to perform a detailed colorization step.
3. The verifier will validate the quality of the colorization.

---

## 2. Schema & CLI Interface

### 2.1. `RestorationState`
We add `no_colorize` to `RestorationState` in [photo_repair/state.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/state.py):
```python
class RestorationState(BaseModel):
    # Skip colorization flag
    no_colorize: bool = False
```

### 2.2. CLI parser (`photo_repair/cli.py`)
We add `--no-colorize`:
```python
parser.add_argument(
    "--no-colorize",
    action="store_true",
    help="Do not colorize the image if it is black and white.",
)
```

---

## 3. Prompts & Execution Changes

### 3.1. `PLANNING_PROMPT`
We add a `{colorize_directive}` placeholder:
```python
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
```

### 3.2. Caching Directive Logic in `ImageClient.plan`
```python
is_bw = analysis.is_black_and_white
colorize = is_bw and not no_colorize

if colorize:
    colorize_directive = (
        "CRITICAL: The photograph is black and white, and colorization is requested. "
        "You MUST include a detailed colorization step in your plan. Specify realistic, natural, "
        "and historically accurate colors for skin, hair, clothing, and the background environment "
        "appropriate to the era."
    )
else:
    colorize_directive = (
        "The photograph should remain in black and white (or match its original color layout). "
        "Maintain the original tonality and nostalgic exposure qualities."
    )
```

### 3.3. `VERIFY_PROMPT`
We update the verifier instructions under `quality_ok` to check colorization quality:
```python
VERIFY_PROMPT = (
    "You are reviewing a restored photograph (second image) against its original (first image).\n"
    "Examine both images and check the following criteria strictly. If a criterion is violated, "
    "set its field to false and list the reason in 'issues':\n\n"
    "... "
    "8. quality_ok: True if overall restoration is clean, professional, and high quality. "
    "Note: If the original is black and white but the restored is colorized, verify that the colorization "
    "is natural, realistic, and period-appropriate (no modern neon shades, cartoonish skin tones, or bleeding colors).\n\n"
    "Identify any issues carefully."
)
```

---

## 4. File Modifications Map

- **`photo_repair/state.py`**:
  - Add `no_colorize` to `RestorationState`.
- **`photo_repair/cli.py`**:
  - Add `--no-colorize` parser option.
  - Pass `no_colorize` when building default runner and executing `restore_photo()`.
- **`photo_repair/graph.py`**:
  - Add `no_colorize` parameter to `restore_photo()` signature and propagate to initial state.
- **`photo_repair/prompts.py`**:
  - Add `{colorize_directive}` placeholder to `PLANNING_PROMPT`.
  - Update `VERIFY_PROMPT` to verify colorization quality.
- **`photo_repair/image_client.py`**:
  - Update `client.plan()` method signature to accept `no_colorize: bool = False`.
  - Format `PLANNING_PROMPT` with the dynamic `colorize_directive`.
- **`photo_repair/nodes.py`**:
  - Update `plan_node()` to pass `state.no_colorize` to `client.plan()`.
- **`tests/`**:
  - Update all tests to check the parsing and execution flow of `no_colorize` correctly.

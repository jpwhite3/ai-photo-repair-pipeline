# Implementation Plan: Automatic Photo Colorization

This plan outlines the step-by-step tasks required to implement the default colorization logic for black and white photographs as specified in the [Design Document](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/docs/superpowers/specs/2026-06-14-photo-restoration-colorization-design.md).

---

## 1. Tasks

### Task 1: Update RestorationState Schema
- **Files to modify:**
  - [photo_repair/state.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/state.py)
  - [tests/test_state.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/tests/test_state.py)
- **Changes:**
  - Add `no_colorize: bool = False` to `RestorationState`.
  - Update `test_restoration_state_defaults` in `test_state.py` to verify `state.no_colorize` defaults to False.
- **Verification:**
  - Run `uv run pytest tests/test_state.py`.

### Task 2: Integrate CLI --no-colorize and Graph Parameters
- **Files to modify:**
  - [photo_repair/graph.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/graph.py)
  - [photo_repair/cli.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/cli.py)
  - [tests/test_cli.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/tests/test_cli.py)
  - [tests/test_graph.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/tests/test_graph.py)
- **Changes:**
  - Update `restore_photo` in `photo_repair/graph.py` to accept `no_colorize` and set it in `RestorationState`.
  - Add `--no-colorize` to CLI parsing arguments in `photo_repair/cli.py`.
  - Accept `no_colorize` in `_build_default_runner` and thread it to `restore_photo`.
  - Update test cases in `test_cli.py` and `test_graph.py` to match the new signatures.
- **Verification:**
  - Run `uv run pytest tests/test_cli.py tests/test_graph.py`.

### Task 3: Update Prompt Definitions
- **Files to modify:**
  - [photo_repair/prompts.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/prompts.py)
  - [tests/test_state.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/tests/test_state.py)
- **Changes:**
  - Add the `{colorize_directive}` placeholder to `PLANNING_PROMPT` in `photo_repair/prompts.py`.
  - Update `VERIFY_PROMPT` to add specific checks verifying colorization quality (natural shades, no neon colors/bleeding).
  - Update tests checking `PLANNING_PROMPT` format in `tests/test_state.py` (ensure we pass a mock placeholder or test formats safely).
- **Verification:**
  - Run `uv run pytest tests/test_state.py`.

### Task 4: Implement Dynamic Directives in Client & Nodes
- **Files to modify:**
  - [photo_repair/image_client.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/image_client.py)
  - [photo_repair/nodes.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/nodes.py)
  - [tests/test_image_client.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/tests/test_image_client.py)
  - [tests/test_nodes.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/tests/test_nodes.py)
- **Changes:**
  - Update `ImageClient.plan` signature to accept `no_colorize: bool = False`.
  - Implement dynamic `colorize_directive` generation based on `analysis.is_black_and_white` and `no_colorize` in `ImageClient.plan`. Format `PLANNING_PROMPT` with this directive.
  - Update `plan_node` in `photo_repair/nodes.py` to pass `state.no_colorize` to `client.plan`.
  - Update unit tests in `test_image_client.py` and `test_nodes.py` to verify colorize directive is formatted correctly under default and force-disabled paths.
- **Verification:**
  - Run `uv run pytest tests/test_image_client.py tests/test_nodes.py`.

### Task 5: Final Check & Linting
- **Verification:**
  - Run the entire test suite: `uv run pytest`.
  - Run `uv run ruff check .` to verify code format.

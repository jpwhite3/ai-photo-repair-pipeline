# Implementation Plan: Optimized Photo Restoration Workflow

This plan outlines the step-by-step tasks required to implement the optimized photo restoration workflow as specified in the [Design Document](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/docs/superpowers/specs/2026-06-14-photo-restoration-workflow-design.md).

---

## 1. Prerequisites & Validation

Before commencing, run the test suite to establish a clean baseline:
```bash
uv run pytest
```
*(Note: One test `test_restoration_prompt_is_verbatim` is currently failing in the repository because the code in `photo_repair/prompts.py` was previously updated with a newer prompt structure, but the test assertion was not updated. The first task will address updating this test assertion to match the code.)*

---

## 2. Tasks

### Task 1: Fix Baseline Test and Update State Schemas
- **Files to modify:**
  - [tests/test_state.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/tests/test_state.py)
  - [photo_repair/state.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/state.py)
- **Changes:**
  - Update `test_restoration_prompt_is_verbatim` in `tests/test_state.py` to match the current content of `photo_repair/prompts.py`.
  - Add `plan: str | None = None` to `RestorationState` class in `photo_repair/state.py`.
  - Add the new fields to `VerificationResult` in `photo_repair/state.py`:
    - `clothing_preserved: bool`
    - `environment_preserved: bool`
    - `no_hallucinations_or_artifacts: bool`
    - `text_and_signage_preserved: bool`
    - `tonality_and_grain_preserved: bool`
  - Update `passed` property in `VerificationResult` to require all boolean checks to be True.
- **Verification:**
  - Run `uv run pytest tests/test_state.py` and ensure the state tests pass.

### Task 2: Implement Planning & Verification Prompts
- **Files to modify:**
  - [photo_repair/prompts.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/prompts.py)
- **Changes:**
  - Define `PLANNING_PROMPT` as a template for planning.
  - Implement `build_restore_prompt(plan: str, issues: list[str] | None = None) -> str`.
  - Update `VERIFY_PROMPT` to instruct the vision model on verifying all the new fields in `VerificationResult`.
- **Verification:**
  - Run `uv run pytest tests/test_state.py` to ensure prompts are correctly imported and defined.

### Task 3: Update ImageClient
- **Files to modify:**
  - [photo_repair/image_client.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/image_client.py)
- **Changes:**
  - Add `plan(self, image_bytes: bytes, mime_type: str, analysis: RestorationAnalysis) -> str` to vision/text model client.
  - Update `restore(self, image_bytes: bytes, mime_type: str, plan: str, issues: list[str] | None = None) -> bytes` to use `build_restore_prompt` with the plan and feedback issues.
- **Verification:**
  - Update mock tests in `tests/test_image_client.py` to support `plan` and updated `restore`/`verify` methods, then run `uv run pytest tests/test_image_client.py`.

### Task 4: Implement Plan Node & Update Restore/Verify Nodes
- **Files to modify:**
  - [photo_repair/nodes.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/nodes.py)
- **Changes:**
  - Implement `plan_node(state: RestorationState, client: ImageClient) -> dict`.
  - Update `restore_node` to fetch `state.plan` and pass it (plus `state.verification.issues` on retries) to `client.restore`.
- **Verification:**
  - Add/update tests in `tests/test_nodes.py` to cover the new `plan_node` behavior, and ensure it correctly handles exceptions and gracefully falls back to default values.
  - Run `uv run pytest tests/test_nodes.py`.

### Task 5: Integrate Plan Node into LangGraph Graph
- **Files to modify:**
  - [photo_repair/graph.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/graph.py)
- **Changes:**
  - Register `"plan"` node in the graph via `graph.add_node("plan", ...)`.
  - Update the edges from `START -> analyze -> restore` to `START -> analyze -> plan -> restore`.
- **Verification:**
  - Run `uv run pytest tests/test_graph.py` to verify the LangGraph compiles and functions correctly.

### Task 6: Final Verification & CLI Check
- **Verification:**
  - Run the entire test suite: `uv run pytest`.
  - Run `uv run ruff check .` to check for formatting or linting issues.

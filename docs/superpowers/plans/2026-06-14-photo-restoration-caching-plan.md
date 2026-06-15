# Implementation Plan: Photo Restoration Caching & Idempotency

This plan outlines the step-by-step tasks required to implement caching of restoration analysis and plans as specified in the [Design Document](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/docs/superpowers/specs/2026-06-14-photo-restoration-caching-design.md).

---

## 1. Tasks

### Task 1: Update RestorationState Schema
- **Files to modify:**
  - [photo_repair/state.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/state.py)
- **Changes:**
  - Add `base_dir: str = "restored_photos"` to `RestorationState`.
  - Add `force: bool = False` to `RestorationState`.
- **Verification:**
  - Run `uv run pytest tests/test_state.py`.

### Task 2: Implement Caching Helpers in storage.py
- **Files to modify:**
  - [photo_repair/storage.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/storage.py)
  - [tests/test_storage.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/tests/test_storage.py)
- **Changes:**
  - Implement `get_image_hash(image_bytes: bytes) -> str` (SHA-256 hash).
  - Implement `get_cached_analysis(base_dir: str, image_hash: str) -> RestorationAnalysis | None`.
  - Implement `save_cached_analysis(base_dir: str, image_hash: str, analysis: RestorationAnalysis) -> None`.
  - Implement `get_cached_plan(base_dir: str, image_hash: str) -> str | None`.
  - Implement `save_cached_plan(base_dir: str, image_hash: str, plan: str) -> None`.
  - Add unit tests verifying all cache helper operations under `tests/test_storage.py`.
- **Verification:**
  - Run `uv run pytest tests/test_storage.py`.

### Task 3: Integrate Force Flag in graph.py and cli.py
- **Files to modify:**
  - [photo_repair/graph.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/graph.py)
  - [photo_repair/cli.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/cli.py)
- **Changes:**
  - Add `force: bool = False` parameter to `restore_photo` in `photo_repair/graph.py` and pass it when instantiating `RestorationState`.
  - Add `--force` action argument in `photo_repair/cli.py`'s `_parse_args`.
  - Accept `force` parameter in `_build_default_runner` and pass it down.
- **Verification:**
  - Run `uv run pytest tests/test_graph.py` and `uv run pytest tests/test_cli.py`.

### Task 4: Implement Cache Lookups in analyze_node and plan_node
- **Files to modify:**
  - [photo_repair/nodes.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/photo_repair/nodes.py)
  - [tests/test_nodes.py](file:///Users/jpwhite/Code/ai-photo-repair-pipeline/tests/test_nodes.py)
- **Changes:**
  - In `analyze_node`, compute the hash of image bytes. If `state.force` is `False`, check for cached analysis. If hit, return it. If miss, run live API call and write cache.
  - In `plan_node`, compute hash of image bytes. If `state.force` is `False`, check for cached plan. If hit, return it. If miss, run live API call and write cache.
  - Add unit tests in `tests/test_nodes.py` verifying cache hit behavior (assert mock client is NOT called) and cache miss behavior (assert mock client IS called and writes to cache).
- **Verification:**
  - Run `uv run pytest tests/test_nodes.py`.

### Task 5: Final suite check & Linting
- **Verification:**
  - Run `uv run pytest` to ensure all 40+ tests pass cleanly.
  - Run `uv run ruff check .` to verify code format.

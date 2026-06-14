# ai-photo-repair-pipeline

Cloud-based AI pipeline to repair old or damaged photos.

It analyzes a photograph, restores it with period-accurate techniques (damage/scratch
removal, colorization, sharpening, denoise), verifies that the composition and the people
in it are unchanged, and saves the result — all driven by Google's Gemini image models.

## How it works

A [LangGraph](https://langchain-ai.github.io/langgraph/) state machine threads one image
through four nodes, with a bounded retry loop if the result fails verification:

```
START → analyze → restore → verify → finalize → END
                    ^___________|  (retry while attempts remain)
```

- **analyze** — Gemini vision detects the era, original photographic process, and defects
  (saved as `analysis.json`).
- **restore** — Gemini 2.5 Flash Image edits the photo using a fixed, verbatim restoration
  prompt plus the analysis as context.
- **verify** — Gemini vision confirms the composition and every person's appearance are
  unchanged and the quality is acceptable (saved as `verification.json`).
- **finalize** — writes a timestamped output directory.

The restoration model id lives in a single config value (`RESTORE_IMAGE_MODEL`) so it can
be swapped without touching code.

## Setup

Requires Python 3.11+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
cp env.example .env   # then add your GOOGLE_API_KEY
```

Get a key at <https://aistudio.google.com/app/apikey> (one key covers the image + vision
models).

## Usage

```bash
# Restore a single image
uv run photo-repair path/to/photo.jpg

# Restore every image in a folder
uv run photo-repair path/to/folder/ --batch

# Override the output directory
uv run photo-repair photo.jpg --out ./results
```

Each run creates a timestamped directory under `OUTPUT_DIR` containing the restored image,
a copy of the original, `analysis.json`, and `verification.json`.

## Development

```bash
uv run pytest          # unit tests (Google API is mocked — no network/keys needed)
uv run ruff check .    # lint
```

The package layout:

| File | Responsibility |
|------|----------------|
| `photo_repair/config.py` | Env-driven settings (API key, model ids, retries, output dir) |
| `photo_repair/prompts.py` | The verbatim restoration prompt + analysis/verify prompts |
| `photo_repair/state.py` | Pydantic models threaded through the graph |
| `photo_repair/image_client.py` | google-genai wrapper (analyze / restore / verify) |
| `photo_repair/nodes.py` | Graph node functions with per-node retry + fallback |
| `photo_repair/graph.py` | Builds and runs the LangGraph state machine |
| `photo_repair/storage.py` | Timestamped artifact output |
| `photo_repair/cli.py` | Command-line interface (single image + `--batch`) |

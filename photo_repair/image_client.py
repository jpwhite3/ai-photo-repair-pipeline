"""Thin wrapper around the google-genai SDK for the restoration pipeline.

Three capabilities, all via ``client.models.generate_content``:
  - ``analyze``: vision model → structured RestorationAnalysis
  - ``restore``: image model → restored image bytes (uses the verbatim RESTORATION_PROMPT)
  - ``verify``: vision model compares original vs restored → VerificationResult

The genai client is injected so the pipeline can be unit-tested without live API calls.
"""

from __future__ import annotations

from google import genai
from google.genai import types

from photo_repair.config import Settings, get_settings
from photo_repair.prompts import (
    ANALYSIS_PROMPT,
    PLANNING_PROMPT,
    VERIFY_PROMPT,
    build_restore_prompt,
)
from photo_repair.state import RestorationAnalysis, VerificationResult


class ImageClient:
    """Wraps a ``google.genai`` client with restoration-specific calls."""

    def __init__(self, client, restore_model: str, analysis_model: str) -> None:
        self._client = client
        self._restore_model = restore_model
        self._analysis_model = analysis_model

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        restore_model: str | None = None,
        analysis_model: str | None = None,
    ) -> ImageClient:
        """Build a client from settings, optionally overriding the model ids."""
        settings = settings or get_settings()
        client = genai.Client(api_key=settings.google_api_key.get_secret_value())
        return cls(
            client,
            restore_model=restore_model or settings.restore_image_model,
            analysis_model=analysis_model or settings.analysis_model,
        )

    # -- public API -------------------------------------------------------------

    def analyze(self, image_bytes: bytes, mime_type: str) -> RestorationAnalysis:
        """Characterise the photo (era, process, defects) as structured data."""
        response = self._client.models.generate_content(
            model=self._analysis_model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                types.Part.from_text(text=ANALYSIS_PROMPT),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RestorationAnalysis,
            ),
        )
        return self._coerce(response.parsed, RestorationAnalysis)

    def plan(
        self,
        image_bytes: bytes,
        mime_type: str,
        analysis: RestorationAnalysis,
        no_colorize: bool = False,
    ) -> str:
        """Generate a step-by-step restoration plan based on analysis."""
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

        prompt_text = PLANNING_PROMPT.format(
            era=analysis.era,
            process=analysis.photographic_process,
            defects=", ".join(analysis.defects),
            is_bw="Yes" if is_bw else "No",
            colorize_directive=colorize_directive,
        )
        response = self._client.models.generate_content(
            model=self._analysis_model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                types.Part.from_text(text=prompt_text),
            ],
        )
        return response.text

    def restore(
        self, image_bytes: bytes, mime_type: str, plan: str, issues: list[str] | None = None
    ) -> bytes:
        """Restore the photo, returning the new image bytes.

        Sends the dynamic prompt (plan + issues) alongside the source image.
        """
        prompt_text = build_restore_prompt(plan, issues)
        response = self._client.models.generate_content(
            model=self._restore_model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                types.Part.from_text(text=prompt_text),
            ],
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )
        return self._extract_image_bytes(response)

    def verify(
        self, original_bytes: bytes, restored_bytes: bytes, mime_type: str
    ) -> VerificationResult:
        """Compare restored vs original; confirm composition and identity preserved."""
        response = self._client.models.generate_content(
            model=self._analysis_model,
            contents=[
                types.Part.from_text(text=VERIFY_PROMPT),
                types.Part.from_bytes(data=original_bytes, mime_type=mime_type),
                types.Part.from_bytes(data=restored_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VerificationResult,
            ),
        )
        return self._coerce(response.parsed, VerificationResult)

    # -- helpers ----------------------------------------------------------------

    @staticmethod
    def _extract_image_bytes(response) -> bytes:
        """Return the first inline image payload from a generate_content response."""
        for part in getattr(response, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            data = getattr(inline, "data", None) if inline is not None else None
            if data:
                return data
        raise RuntimeError("Model returned no image data for the restoration request.")

    @staticmethod
    def _coerce(parsed, model_cls):
        """Return ``parsed`` as ``model_cls`` (the SDK may hand back a dict)."""
        if isinstance(parsed, model_cls):
            return parsed
        if isinstance(parsed, dict):
            return model_cls.model_validate(parsed)
        raise RuntimeError(f"Model returned no parsable {model_cls.__name__}.")

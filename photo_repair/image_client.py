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
from photo_repair.prompts import ANALYSIS_PROMPT, RESTORATION_PROMPT, VERIFY_PROMPT
from photo_repair.state import RestorationAnalysis, VerificationResult


class ImageClient:
    """Wraps a ``google.genai`` client with restoration-specific calls."""

    def __init__(self, client, restore_model: str, analysis_model: str) -> None:
        self._client = client
        self._restore_model = restore_model
        self._analysis_model = analysis_model

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> ImageClient:
        settings = settings or get_settings()
        client = genai.Client(api_key=settings.google_api_key.get_secret_value())
        return cls(
            client,
            restore_model=settings.restore_image_model,
            analysis_model=settings.analysis_model,
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

    def restore(self, image_bytes: bytes, mime_type: str) -> bytes:
        """Restore the photo, returning the new image bytes.

        Sends the user's verbatim RESTORATION_PROMPT alongside the source image.
        """
        response = self._client.models.generate_content(
            model=self._restore_model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                types.Part.from_text(text=RESTORATION_PROMPT),
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

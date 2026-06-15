"""State models carried through the LangGraph restoration pipeline."""


from pydantic import BaseModel, Field


class RestorationAnalysis(BaseModel):
    """Structured assessment of the photo produced by the analyze node."""

    era: str = Field(description="Approximate era the photo was taken, e.g. '1950s'.")
    photographic_process: str = Field(
        description="Likely original process, e.g. 'gelatin silver print'."
    )
    defects: list[str] = Field(
        default_factory=list, description="Visible age-related defects."
    )
    is_black_and_white: bool = Field(
        default=False, description="Whether the original is black and white."
    )
    notes: str = Field(default="", description="Any extra observations.")


class VerificationResult(BaseModel):
    """Result of the verify node's QA check on the restored image."""

    composition_preserved: bool = Field(
        description="True if framing/crop/layout is unchanged."
    )
    identity_preserved: bool = Field(
        description="True if no person's appearance/identity changed."
    )
    clothing_preserved: bool = Field(
        description="True if clothing style, details, fabrics, and patterns match."
    )
    environment_preserved: bool = Field(
        description="True if scenery, background details, lighting, and objects match."
    )
    no_hallucinations_or_artifacts: bool = Field(
        description="True if free of extra limbs, floating artifacts, or distortions."
    )
    text_and_signage_preserved: bool = Field(
        description="True if text/writing is legible and matches the original."
    )
    tonality_and_grain_preserved: bool = Field(
        description="True if authentic film grain and exposure contrast are kept (no plastic/over-smoothed look)."
    )
    quality_ok: bool = Field(description="True if technical quality is acceptable.")
    issues: list[str] = Field(default_factory=list, description="Problems found, if any.")

    @property
    def passed(self) -> bool:
        """The restoration passes only if all hard constraints and quality hold."""
        return (
            self.composition_preserved
            and self.identity_preserved
            and self.clothing_preserved
            and self.environment_preserved
            and self.no_hallucinations_or_artifacts
            and self.text_and_signage_preserved
            and self.tonality_and_grain_preserved
            and self.quality_ok
        )


class RestorationState(BaseModel):
    """The single object threaded through every graph node.

    ``bytes`` fields hold raw image data; LangGraph merges node return dicts into this.
    """

    model_config = {"arbitrary_types_allowed": True}

    # Input
    input_path: str
    image_bytes: bytes
    mime_type: str = "image/png"

    # Intermediate / outputs
    analysis: RestorationAnalysis | None = None
    plan: str | None = None
    restored_bytes: bytes | None = None
    verification: VerificationResult | None = None
    output_path: str | None = None

    # Bookkeeping
    attempts: int = 0
    notes: list[str] = Field(default_factory=list)
    current_step: str = "initialized"

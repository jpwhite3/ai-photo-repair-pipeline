"""Configuration for the photo restoration pipeline.

Environment-driven settings (with .env support). The restoration engine model id is
isolated to a single constant (``restore_image_model``) so it is swappable.
"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings, loaded from environment variables / a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Required: single Google API key (https://aistudio.google.com/app/apikey).
    google_api_key: SecretStr = Field(..., alias="GOOGLE_API_KEY")

    # The image-editing model that performs the restoration. Swap this one value to
    # point at a different Google image model.
    restore_image_model: str = Field("gemini-3.1-flash-lite", alias="RESTORE_IMAGE_MODEL")

    # Vision model used for damage/era analysis and post-restoration verification.
    analysis_model: str = Field("gemini-2.5-flash", alias="ANALYSIS_MODEL")

    # How many times the restore step may be retried when verification fails.
    max_restore_attempts: int = Field(2, ge=1, le=10, alias="MAX_RESTORE_ATTEMPTS")

    # Base directory for restored output (one timestamped subdir per run).
    output_dir: str = Field("restored_photos", alias="OUTPUT_DIR")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()

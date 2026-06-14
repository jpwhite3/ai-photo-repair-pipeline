"""Tests for photo_repair.config."""

import pytest


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from photo_repair.config import Settings

    settings = Settings()
    assert settings.google_api_key.get_secret_value() == "test-key"


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from photo_repair.config import Settings

    settings = Settings()
    assert settings.restore_image_model == "gemini-3.1-flash-image"
    assert settings.analysis_model == "gemini-3.1-flash-lite"
    assert settings.max_restore_attempts == 2
    assert settings.output_dir == "restored_photos"


def test_settings_overrides_from_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("RESTORE_IMAGE_MODEL", "some-other-model")
    monkeypatch.setenv("MAX_RESTORE_ATTEMPTS", "5")
    from photo_repair.config import Settings

    settings = Settings()
    assert settings.restore_image_model == "some-other-model"
    assert settings.max_restore_attempts == 5


def test_settings_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from photo_repair.config import Settings

    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_get_settings_is_cached(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from photo_repair.config import get_settings

    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b

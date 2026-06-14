"""Tests for photo_repair.image_client (google-genai mocked — no live API)."""

import types as pytypes

import pytest


def _fake_part(image_bytes=None, text=None):
    """Build an object shaped like a google.genai response Part."""
    inline = pytypes.SimpleNamespace(data=image_bytes) if image_bytes is not None else None
    return pytypes.SimpleNamespace(inline_data=inline, text=text)


def _fake_response(parts=None, parsed=None):
    return pytypes.SimpleNamespace(parts=parts or [], parsed=parsed)


def _make_client(mocker, response):
    genai_client = mocker.Mock()
    genai_client.models.generate_content.return_value = response
    return genai_client


def test_restore_sends_verbatim_prompt_and_returns_image_bytes(mocker):
    from photo_repair.image_client import ImageClient
    from photo_repair.prompts import RESTORATION_PROMPT

    response = _fake_response(
        parts=[_fake_part(text="here you go"), _fake_part(image_bytes=b"NEWIMG")]
    )
    genai_client = _make_client(mocker, response)
    client = ImageClient(genai_client, restore_model="img-model", analysis_model="vision-model")

    out = client.restore(b"OLDIMG", "image/jpeg")

    assert out == b"NEWIMG"
    call = genai_client.models.generate_content.call_args
    assert call.kwargs["model"] == "img-model"
    # The verbatim restoration prompt must be passed through to the model.
    sent_text = " ".join(
        getattr(p, "text", "") or "" for p in call.kwargs["contents"] if getattr(p, "text", None)
    )
    assert RESTORATION_PROMPT in sent_text


def test_restore_raises_when_no_image_returned(mocker):
    from photo_repair.image_client import ImageClient

    response = _fake_response(parts=[_fake_part(text="refused")])
    genai_client = _make_client(mocker, response)
    client = ImageClient(genai_client, restore_model="img-model", analysis_model="vision-model")

    with pytest.raises(RuntimeError):
        client.restore(b"OLDIMG", "image/jpeg")


def test_analyze_returns_parsed_analysis(mocker):
    from photo_repair.image_client import ImageClient
    from photo_repair.state import RestorationAnalysis

    parsed = RestorationAnalysis(
        era="1960s", photographic_process="color negative", defects=["fading"]
    )
    genai_client = _make_client(mocker, _fake_response(parsed=parsed))
    client = ImageClient(genai_client, restore_model="img-model", analysis_model="vision-model")

    result = client.analyze(b"OLDIMG", "image/jpeg")

    assert isinstance(result, RestorationAnalysis)
    assert result.era == "1960s"
    assert genai_client.models.generate_content.call_args.kwargs["model"] == "vision-model"


def test_from_settings_allows_model_override(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "k")
    from photo_repair.config import get_settings
    from photo_repair.image_client import ImageClient

    get_settings.cache_clear()
    client = ImageClient.from_settings(restore_model="custom-restore-model")
    assert client._restore_model == "custom-restore-model"
    # Untouched override falls back to the configured default.
    assert client._analysis_model == "gemini-2.5-flash"


def test_verify_returns_parsed_verification_with_both_images(mocker):
    from photo_repair.image_client import ImageClient
    from photo_repair.state import VerificationResult

    parsed = VerificationResult(
        composition_preserved=True, identity_preserved=True, quality_ok=True, issues=[]
    )
    genai_client = _make_client(mocker, _fake_response(parsed=parsed))
    client = ImageClient(genai_client, restore_model="img-model", analysis_model="vision-model")

    result = client.verify(b"ORIG", b"RESTORED", "image/jpeg")

    assert isinstance(result, VerificationResult)
    assert result.passed is True
    # Both images must be supplied to the verifier.
    contents = genai_client.models.generate_content.call_args.kwargs["contents"]
    image_parts = [p for p in contents if getattr(p, "inline_data", None) is not None]
    assert len(image_parts) >= 2

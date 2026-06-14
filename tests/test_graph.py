"""End-to-end graph tests with a mocked image client (no live API)."""

from photo_repair.state import RestorationAnalysis, VerificationResult


def _analysis():
    return RestorationAnalysis(era="1950s", photographic_process="silver print", defects=["fade"])


def _passing():
    return VerificationResult(
        composition_preserved=True, identity_preserved=True, quality_ok=True, issues=[]
    )


def _failing():
    return VerificationResult(
        composition_preserved=False, identity_preserved=True, quality_ok=True, issues=["crop"]
    )


def test_happy_path_runs_once(mocker, tmp_path):
    from photo_repair.graph import restore_photo

    client = mocker.Mock()
    client.analyze.return_value = _analysis()
    client.restore.return_value = b"RESTORED"
    client.verify.return_value = _passing()

    final = restore_photo(
        image_bytes=b"OLD",
        input_path="grandpa.jpg",
        client=client,
        mime_type="image/jpeg",
        max_attempts=2,
        base_dir=str(tmp_path),
    )

    assert final.current_step == "completed"
    assert final.restored_bytes == b"RESTORED"
    assert final.verification.passed is True
    assert final.output_path
    assert client.restore.call_count == 1


def test_retry_loop_reattempts_then_finalizes(mocker, tmp_path):
    from photo_repair.graph import restore_photo

    client = mocker.Mock()
    client.analyze.return_value = _analysis()
    client.restore.side_effect = [b"FIRST", b"SECOND"]
    client.verify.side_effect = [_failing(), _passing()]

    final = restore_photo(
        image_bytes=b"OLD",
        input_path="grandpa.jpg",
        client=client,
        mime_type="image/jpeg",
        max_attempts=2,
        base_dir=str(tmp_path),
    )

    assert client.restore.call_count == 2
    assert final.verification.passed is True
    assert final.current_step == "completed"


def test_retry_stops_at_max_attempts(mocker, tmp_path):
    from photo_repair.graph import restore_photo

    client = mocker.Mock()
    client.analyze.return_value = _analysis()
    client.restore.return_value = b"RESTORED"
    client.verify.return_value = _failing()  # never passes

    final = restore_photo(
        image_bytes=b"OLD",
        input_path="grandpa.jpg",
        client=client,
        mime_type="image/jpeg",
        max_attempts=3,
        base_dir=str(tmp_path),
    )

    assert client.restore.call_count == 3  # bounded by max_attempts
    assert final.current_step == "completed"
    assert final.verification.passed is False

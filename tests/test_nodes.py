"""Tests for photo_repair.nodes (image client mocked)."""

from photo_repair.state import RestorationAnalysis, RestorationState, VerificationResult


def _state(**kw):
    base = {"input_path": "p.jpg", "image_bytes": b"OLD", "mime_type": "image/jpeg"}
    base.update(kw)
    return RestorationState(**base)


def _passing_verification():
    return VerificationResult(
        composition_preserved=True,
        identity_preserved=True,
        clothing_preserved=True,
        environment_preserved=True,
        no_hallucinations_or_artifacts=True,
        text_and_signage_preserved=True,
        tonality_and_grain_preserved=True,
        quality_ok=True,
        issues=[],
    )


def _failing_verification():
    return VerificationResult(
        composition_preserved=False,
        identity_preserved=True,
        clothing_preserved=True,
        environment_preserved=True,
        no_hallucinations_or_artifacts=True,
        text_and_signage_preserved=True,
        tonality_and_grain_preserved=True,
        quality_ok=True,
        issues=["crop"],
    )


def test_analyze_node_success(mocker, tmp_path):
    from photo_repair.nodes import analyze_node

    client = mocker.Mock()
    client.analyze.return_value = RestorationAnalysis(
        era="1950s", photographic_process="silver print", defects=["fading"]
    )
    update = analyze_node(_state(base_dir=str(tmp_path)), client)
    assert update["analysis"].era == "1950s"
    assert update["current_step"] == "analyzed"


def test_analyze_node_falls_back_on_error(mocker, tmp_path):
    from photo_repair.nodes import analyze_node

    client = mocker.Mock()
    client.analyze.side_effect = RuntimeError("boom")
    update = analyze_node(_state(base_dir=str(tmp_path)), client)
    assert isinstance(update["analysis"], RestorationAnalysis)  # fallback, not a crash


def test_plan_node_success(mocker, tmp_path):
    from photo_repair.nodes import plan_node

    client = mocker.Mock()
    client.plan.return_value = "RESTORE PLAN"
    analysis = RestorationAnalysis(era="1950s", photographic_process="silver print", defects=["fading"])
    state = _state(analysis=analysis, base_dir=str(tmp_path))
    update = plan_node(state, client)
    assert update["plan"] == "RESTORE PLAN"
    assert update["current_step"] == "planned"
    client.plan.assert_called_once_with(b"OLD", "image/jpeg", analysis)


def test_plan_node_falls_back_on_error(mocker, tmp_path):
    from photo_repair.nodes import plan_node

    client = mocker.Mock()
    client.plan.side_effect = RuntimeError("boom")
    update = plan_node(_state(base_dir=str(tmp_path)), client)
    assert "Restore the photo" in update["plan"]
    assert update["current_step"] == "planned"


def test_restore_node_increments_attempts_and_sets_bytes(mocker):
    from photo_repair.nodes import restore_node

    client = mocker.Mock()
    client.restore.return_value = b"NEW"
    state = _state(attempts=0, plan="PLAN HERE")
    update = restore_node(state, client)
    assert update["restored_bytes"] == b"NEW"
    assert update["attempts"] == 1
    client.restore.assert_called_once_with(b"OLD", "image/jpeg", "PLAN HERE", None)


def test_restore_node_passes_plan_and_issues(mocker):
    from photo_repair.nodes import restore_node

    client = mocker.Mock()
    client.restore.return_value = b"NEW"
    state = _state(attempts=1, plan="PLAN HERE", verification=_failing_verification())
    update = restore_node(state, client)
    assert update["restored_bytes"] == b"NEW"
    client.restore.assert_called_once_with(b"OLD", "image/jpeg", "PLAN HERE", ["crop"])


def test_restore_node_records_failure_without_crashing(mocker):
    from photo_repair.nodes import restore_node

    client = mocker.Mock()
    client.restore.side_effect = RuntimeError("api down")
    update = restore_node(_state(attempts=1), client)
    assert update["restored_bytes"] is None
    assert update["attempts"] == 2


def test_verify_node_fails_when_no_restored_image(mocker):
    from photo_repair.nodes import verify_node

    client = mocker.Mock()
    update = verify_node(_state(restored_bytes=None), client)
    assert update["verification"].passed is False
    client.verify.assert_not_called()


def test_verify_node_returns_result(mocker):
    from photo_repair.nodes import verify_node

    client = mocker.Mock()
    client.verify.return_value = _passing_verification()
    update = verify_node(_state(restored_bytes=b"NEW"), client)
    assert update["verification"].passed is True


def test_route_after_verify():
    from photo_repair.nodes import route_after_verify

    # Passed -> finalize
    s = _state(restored_bytes=b"x", attempts=1, verification=_passing_verification())
    assert route_after_verify(s, max_attempts=2) == "finalize"

    # Failed but attempts remain -> retry restore
    s = _state(restored_bytes=b"x", attempts=1, verification=_failing_verification())
    assert route_after_verify(s, max_attempts=2) == "restore"

    # Failed and out of attempts -> finalize anyway
    s = _state(restored_bytes=b"x", attempts=2, verification=_failing_verification())
    assert route_after_verify(s, max_attempts=2) == "finalize"


def test_finalize_node_writes_outputs(tmp_path):
    from photo_repair.nodes import finalize_node

    s = _state(restored_bytes=b"NEW", verification=_passing_verification())
    update = finalize_node(s, base_dir=str(tmp_path))
    assert update["current_step"] == "completed"
    assert update["output_path"]
    from pathlib import Path

    assert Path(update["output_path"]).exists()


def test_analyze_node_caching(mocker, tmp_path):
    from photo_repair.nodes import analyze_node

    client = mocker.Mock()
    client.analyze.return_value = RestorationAnalysis(
        era="1950s", photographic_process="silver print", defects=["fading"]
    )

    base_dir = str(tmp_path)
    state = _state(base_dir=base_dir)

    # 1. Cache miss
    update1 = analyze_node(state, client)
    assert update1["analysis"].era == "1950s"
    assert client.analyze.call_count == 1

    # 2. Cache hit (does not call client.analyze again)
    update2 = analyze_node(state, client)
    assert update2["analysis"].era == "1950s"
    assert client.analyze.call_count == 1
    assert "Loaded analysis from cache" in update2["notes"][-1]

    # 3. Force recreate (ignores cache and calls client.analyze)
    state_force = _state(base_dir=base_dir, force=True)
    update3 = analyze_node(state_force, client)
    assert update3["analysis"].era == "1950s"
    assert client.analyze.call_count == 2


def test_plan_node_caching(mocker, tmp_path):
    from photo_repair.nodes import plan_node

    client = mocker.Mock()
    client.plan.return_value = "RESTORE PLAN TEXT"

    base_dir = str(tmp_path)
    state = _state(base_dir=base_dir)

    # 1. Cache miss
    update1 = plan_node(state, client)
    assert update1["plan"] == "RESTORE PLAN TEXT"
    assert client.plan.call_count == 1

    # 2. Cache hit (does not call client.plan again)
    update2 = plan_node(state, client)
    assert update2["plan"] == "RESTORE PLAN TEXT"
    assert client.plan.call_count == 1
    assert "Loaded restoration plan from cache" in update2["notes"][-1]

    # 3. Force recreate (ignores cache and calls client.plan)
    state_force = _state(base_dir=base_dir, force=True)
    update3 = plan_node(state_force, client)
    assert update3["plan"] == "RESTORE PLAN TEXT"
    assert client.plan.call_count == 2

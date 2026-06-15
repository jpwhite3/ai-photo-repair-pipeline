"""Tests for photo_repair.cli (pipeline injected — no live API)."""

from photo_repair.state import RestorationState


def _make_runner(mocker, output="out/dir"):
    def runner(image_bytes, input_path, mime_type):
        return RestorationState(
            input_path=input_path,
            image_bytes=image_bytes,
            mime_type=mime_type,
            restored_bytes=b"NEW",
            output_path=output,
            current_step="completed",
        )

    return mocker.Mock(side_effect=runner)


def test_resolve_inputs_single_file(tmp_path):
    from photo_repair.cli import resolve_inputs

    f = tmp_path / "a.jpg"
    f.write_bytes(b"x")
    assert resolve_inputs(str(f), batch=False) == [f]


def test_resolve_inputs_batch_finds_only_images(tmp_path):
    from photo_repair.cli import resolve_inputs

    (tmp_path / "a.jpg").write_bytes(b"x")
    (tmp_path / "b.png").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("ignore me")
    found = resolve_inputs(str(tmp_path), batch=True)
    names = sorted(p.name for p in found)
    assert names == ["a.jpg", "b.png"]


def test_main_single_image_returns_zero(tmp_path, mocker):
    from photo_repair import cli

    img = tmp_path / "grandpa.jpg"
    img.write_bytes(b"OLD")
    runner = _make_runner(mocker)

    rc = cli.main([str(img)], restore_fn=runner)

    assert rc == 0
    assert runner.call_count == 1
    assert runner.call_args.args[1] == str(img)  # input_path


def test_main_batch_processes_each_image(tmp_path, mocker):
    from photo_repair import cli

    (tmp_path / "a.jpg").write_bytes(b"A")
    (tmp_path / "b.png").write_bytes(b"B")
    runner = _make_runner(mocker)

    rc = cli.main([str(tmp_path), "--batch"], restore_fn=runner)

    assert rc == 0
    assert runner.call_count == 2


def test_main_missing_path_returns_nonzero(tmp_path, mocker):
    from photo_repair import cli

    runner = _make_runner(mocker)
    rc = cli.main([str(tmp_path / "nope.jpg")], restore_fn=runner)
    assert rc != 0
    runner.assert_not_called()


def test_main_empty_folder_returns_nonzero(tmp_path, mocker):
    from photo_repair import cli

    runner = _make_runner(mocker)
    rc = cli.main([str(tmp_path), "--batch"], restore_fn=runner)
    assert rc != 0
    runner.assert_not_called()


def test_parse_args_captures_model_override():
    from photo_repair.cli import _parse_args

    args = _parse_args(["photo.jpg", "--model", "gemini-X", "--force", "--no-colorize"])
    assert args.model == "gemini-X"
    assert args.force is True
    assert args.no_colorize is True
    assert _parse_args(["photo.jpg"]).model is None
    assert _parse_args(["photo.jpg"]).force is False
    assert _parse_args(["photo.jpg"]).no_colorize is False


def test_main_threads_model_override_to_runner(tmp_path, mocker):
    from photo_repair import cli

    img = tmp_path / "a.jpg"
    img.write_bytes(b"x")
    spy = mocker.patch.object(cli, "_build_default_runner", return_value=_make_runner(mocker))

    rc = cli.main([str(img), "--model", "gemini-X", "--force", "--no-colorize"])

    assert rc == 0
    assert spy.call_args.kwargs.get("model_override") == "gemini-X"
    assert spy.call_args.kwargs.get("force") is True
    assert spy.call_args.kwargs.get("no_colorize") is True


def test_main_passes_correct_mime(tmp_path, mocker):
    from photo_repair import cli

    img = tmp_path / "p.png"
    img.write_bytes(b"OLD")
    runner = _make_runner(mocker)

    cli.main([str(img)], restore_fn=runner)
    assert runner.call_args.args[2] == "image/png"  # mime_type

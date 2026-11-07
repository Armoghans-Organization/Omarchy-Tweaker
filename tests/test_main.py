import pytest

from omarchy_tweaker import main


def test_main_prints_welcome_message(capsys: pytest.CaptureFixture[str]) -> None:
    main()

    captured = capsys.readouterr()
    assert captured.out == "Welcome to Omarchy Tweaker!\n"
    assert captured.err == ""

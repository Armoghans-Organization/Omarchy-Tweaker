import pytest

from omarchy_tweaker import main


def test_main_prints_banner_and_welcome_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main()

    captured = capsys.readouterr()
    assert "Omarchy Tweaker" in captured.out
    assert "Welcome to Omarchy Tweaker!" in captured.out
    assert captured.err == ""

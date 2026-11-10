import subprocess
import sys

import pytest

from omarchy_tweaker import main


def test_main_prints_banner_and_welcome_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main([])

    captured = capsys.readouterr()
    assert "Omarchy Tweaker" in captured.out
    assert "Welcome to Omarchy Tweaker!" in captured.out
    assert "System" in captured.out
    assert "OS" in captured.out
    assert "Kernel" in captured.out
    assert "Desktop" in captured.out
    assert "CPU" in captured.out
    assert "Memory" in captured.out
    assert "Disk" in captured.out
    assert "Uptime" in captured.out
    assert captured.err == ""


def test_main_without_arguments_does_not_import_typer() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "from omarchy_tweaker import main; "
                "main([]); "
                "assert 'typer' not in sys.modules"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

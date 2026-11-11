import os
import subprocess
import sys
from pathlib import Path

import pytest

import omarchy_tweaker.functions.cleanup as cleanup_module
from omarchy_tweaker import main
from omarchy_tweaker.functions.logger import LOG_DIR_ENV_VAR


def test_main_prints_banner_and_snapshot_step(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(LOG_DIR_ENV_VAR, str(tmp_path))
    monkeypatch.setattr(cleanup_module, "available_cleanup_items", lambda **kwargs: ())

    main([])

    captured = capsys.readouterr()
    assert "Omarchy Tweaker" in captured.out
    assert "SYSTEM SNAPSHOT" in captured.out
    assert "Snapshot skipped" in captured.out
    assert "CLEANUP" in captured.out
    assert "No installed cleanup items were found." in captured.out
    assert captured.err == ""

    log_files = list(tmp_path.glob("*.log"))
    assert len(log_files) == 1
    content = log_files[0].read_text(encoding="utf-8")
    assert "Snapshot step skipped" in content
    assert "Cleanup step skipped" in content
    assert "APPLICATION SHUTDOWN REPORT" in content


def test_main_without_arguments_does_not_import_typer(tmp_path: Path) -> None:
    env = {**os.environ, LOG_DIR_ENV_VAR: str(tmp_path)}
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
        env=env,
    )

    assert result.returncode == 0, result.stderr

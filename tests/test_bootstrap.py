from __future__ import annotations

import pytest

import omarchy_tweaker
from omarchy_tweaker import error_handling
from omarchy_tweaker_bootstrap import error_handling as bootstrap_error_handling
from omarchy_tweaker_bootstrap import main as bootstrap_main


def test_bootstrap_main_delegates_to_package_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(omarchy_tweaker, "main", lambda: calls.append(True))

    bootstrap_main()

    assert calls == [True]


def test_compatibility_module_reexports_bootstrap_error_handling() -> None:
    assert error_handling.install_error_handling is bootstrap_error_handling.install_error_handling
    assert error_handling.print_exception is bootstrap_error_handling.print_exception
    assert error_handling.ErrorHandlingConfig is bootstrap_error_handling.ErrorHandlingConfig

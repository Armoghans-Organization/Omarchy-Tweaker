"""Compatibility re-exports for the bootstrap error handling module."""

from omarchy_tweaker_bootstrap.error_handling import (
    ErrorHandlingConfig,
    install_error_handling,
    print_exception,
)

__all__ = [
    "ErrorHandlingConfig",
    "install_error_handling",
    "print_exception",
]

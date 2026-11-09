"""Bootstrap entry point for Omarchy Tweaker.

This package installs Rich error handling before importing the application
package. Keeping the bootstrap outside ``omarchy_tweaker`` means syntax and
indentation errors in any application module, including ``__init__.py``, are
rendered by Rich.
"""

from rich import pretty

from omarchy_tweaker_bootstrap.error_handling import install_error_handling

install_error_handling()
pretty.install()


def main() -> None:
    """Install error handling, then run the Omarchy Tweaker CLI."""
    from omarchy_tweaker import main as run

    run()

# Contributing to Omarchy Tweaker

Thank you for your interest in contributing to **Omarchy Tweaker**.

Omarchy Tweaker is a personal customization and automation toolkit for [Omarchy](https://omarchy.org) on Arch Linux. It is primarily developed for the maintainer's personal environment and is **not** intended as a universal, one-size-fits-all installer.

## Getting Started

1. Ensure you have **Python 3.13+** and **uv** installed.
2. Clone the repository.
3. Install dependencies.

```bash
uv sync
```

4. Run the quality checks.

```bash
uv run poe check
```

For changes affecting packaging, documentation, or the complete development pipeline, also run:

```bash
uv run poe ci
```

## Development Workflow

- All development tasks are managed through Poe the Poet.

```bash
uv run poe <task>
```

- Before committing, run the relevant checks.

```bash
uv run poe check
```

## Code Style

- Follow the conventions documented in [`AGENTS.md`](AGENTS.md).
- Type annotations are required; Mypy strict mode is enforced.
- Use Google-style docstrings.
- Keep CLI command definitions separate from business logic.

## Testing

- Add or update tests for new functionality.
- Mock external commands and system interactions.
- Do not modify the real host system during tests.

## System Safety

- Destructive operations require validation, confirmation, and safeguards.
- Never execute privileged or destructive operations without authorization.

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/).

```text
feat: add package management commands
fix: handle missing configuration files
docs: improve installation documentation
```

## Pull Requests

Before opening a pull request, please ensure:

- `uv run poe check` passes locally.
- New functionality is tested.
- Documentation is updated when required.

## Community Standards

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)
- [Support](SUPPORT.md)

## License

Released under the MIT License. See [LICENSE](LICENSE).

# Omarchy Tweaker — Agent Development Guidelines

> Source of truth for AI coding agents and contributors working on this repository.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Repository Structure](#3-repository-structure)
4. [Python Development Standards](#4-python-development-standards)
5. [CLI Architecture and User Experience](#5-cli-architecture-and-user-experience)
6. [System Operations and Safety](#6-system-operations-and-safety)
7. [Error Handling and Logging](#7-error-handling-and-logging)
8. [Configuration and Data Validation](#8-configuration-and-data-validation)
9. [Testing Standards](#9-testing-standards)
10. [Code Quality and Static Analysis](#10-code-quality-and-static-analysis)
11. [Dependency Management](#11-dependency-management)
12. [Development Commands](#12-development-commands)
13. [Documentation Standards](#13-documentation-standards)
14. [Git, Versioning and Release](#14-git-versioning-and-release)
15. [AI Agent Instructions](#15-ai-agent-instructions)
16. [Scope and Project Boundaries](#16-scope-and-project-boundaries)
17. [Disclaimer and Operational Responsibility](#17-disclaimer-and-operational-responsibility)
18. [Agent Execution Report Standard](#18-agent-execution-report-standard)
19. [Final Development Principles](#19-final-development-principles)

---

## 1. Project Overview

- **Project:** Omarchy Tweaker
- **Package:** `omarchy-tweaker`
- **Python module:** `omarchy_tweaker`
- **Description:** A Python-based command-line application for customizing, automating, maintaining, and bootstrapping personal Omarchy installations.
- **Version:** `0.0.0`
- **Python requirement:** `3.13+`
- **Package manager:** `uv`
- **Build backend:** `uv_build`
- **Task runner:** Poe the Poet

Omarchy Tweaker is a Python-based command-line application for customizing, automating, maintaining, and bootstrapping personal Omarchy installations.

The project brings useful system tweaks, configuration management, automation routines, and utilities together in one modular application. It primarily targets Omarchy installations running on Linux, particularly its Arch Linux-based environment.

### Current Status

The repository is in the **scaffolding stage**.

- The only implementation is the CLI entry point in `src/omarchy_tweaker/__init__.py`.
- The entry point currently prints a welcome message.
- No features, commands, modules, or system operations are implemented yet.

Do not assume that a feature is implemented because it is described here, planned here, or referenced in this file. Treat all non-entry-point behavior as **not implemented**.

### Primary Objectives

- Provide a centralized interface for managing Omarchy customizations.
- Automate repetitive system configuration and maintenance tasks.
- Simplify installation, removal, and management of selected packages.
- Provide reusable utilities for interacting with the underlying Linux system.
- Make system customization safer, more predictable, and easier to maintain.
- Keep the application modular, extensible, and maintainable.
- Provide an intuitive terminal experience without unnecessary complexity.

### Development Philosophy

Prioritize the following principles:

1. **Simplicity:** Avoid unnecessary abstractions, dependencies, and complexity.
2. **Modularity:** Keep functionality separated into logical, reusable modules.
3. **Maintainability:** Write readable, documented, consistently structured code.
4. **Reliability:** Handle errors explicitly and avoid unexpected system modifications.
5. **Safety:** Treat system-level operations as potentially destructive.
6. **Performance:** Keep startup time and runtime overhead low.
7. **User Experience:** Provide clear prompts, informative output, and predictable behavior.
8. **Testability:** Design functionality so it can be tested without modifying the host system.
9. **Extensibility:** Allow for future expansion and integration with other tools or workflows.

---

## 2. Technology Stack

Agents must respect the existing technology choices and use established libraries whenever appropriate.

### Runtime Dependencies

| Library | Purpose | Status |
|---|---|---|
| InquirerPy | Interactive prompts, menus, and selection interfaces | Planned |
| Prompt Toolkit | Advanced terminal input handling and interactive interfaces | Planned |
| psutil | System and process information | Planned |
| Pydantic | Data validation, parsing, and settings management | Planned |
| Rich | Terminal formatting, panels, tables, progress indicators, and tracebacks | Planned |
| Typer | CLI commands, arguments, options, and application entry points | Planned |

**Important:** The runtime dependencies above are **planned**. The current `pyproject.toml` declares no runtime dependencies yet.

Do not import a runtime library before it has been added to `pyproject.toml` with `uv add`.

### Development Dependencies

| Library | Purpose |
|---|---|
| Ruff | Python linting and formatting |
| Mypy | Static type checking |
| Pytest | Automated testing |
| Pytest-Mock | Mocking dependencies during tests |
| Pytest-Cov | Test coverage reporting |
| Poe the Poet | Development task automation |

### Documentation Dependencies

| Library | Purpose |
|---|---|
| Zensical | Static documentation site generation |
| Git Cliff | Automated changelog generation |

### Build System

| Tool | Purpose |
|---|---|
| uv | Dependency management, virtual environments, project execution, and builds |
| uv_build | Python package build backend |

### Supported Technologies

- Python 3.13+
- Linux
- Omarchy
- Arch Linux ecosystem
- Typer-based CLI applications
- Rich-based terminal interfaces

Do not introduce another library to solve a problem already adequately handled by an existing dependency.

Before adding a dependency:

- Determine whether the Python standard library can solve the problem.
- Check whether an existing dependency already provides the functionality.
- Consider installation size and runtime overhead.
- Ensure the dependency supports the project's Python version.
- Keep runtime dependencies separate from development and documentation dependencies.

---

## 3. Repository Structure

```text
.
├── AGENTS.md                     [REQUIRED] AI agent development guidance.
├── Readme.md                     [REQUIRED] Human-facing project overview.
├── LICENSE
├── pyproject.toml
├── uv.lock
├── zensical.toml
├── session.sh                    [DEV WORKSPACE] Zellij session launcher.
├── session.kdl                   [DEV WORKSPACE] Zellij layout definition.
├── docs/
│   ├── index.md
│   ├── changelog.md
│   └── release-notes.md
├── src/
│   └── omarchy_tweaker/
│       ├── __init__.py          [IMPLEMENTED] CLI entry point.
│       └── ...                   [TARGET] Not yet implemented.
├── tests/
│   └── test_main.py
└── .github/
    └── workflows/               [REQUIRED] CI, docs, release workflows.

Generated artifacts (never commit): dist/, site/, docs/changelog.md,
docs/release-notes.md, CHANGELOG.md, RELEASE_NOTES.md, .cache/, .pytest_cache/,
.mypy_cache/, .ruff_cache/, .coverage, __pycache__/.
```

The `src/omarchy_tweaker/` layout under `cli/`, `core/`, and `models/` is a **target structure**, not an implemented one. Do not assume it exists when modifying code.

The Zellij session files (`session.sh`, `session.kdl`) are developer-workspace tooling for launching a dedicated terminal session. They are not part of the packaged CLI.

---

## 4. Python Development Standards

### General Requirements

- Use modern Python syntax and features supported by Python 3.13+.
- Follow PEP 8 conventions and the project's Ruff configuration.
- Use meaningful and descriptive identifiers.
- Prefer explicit implementations over unnecessarily clever code.
- Keep functions and classes focused on a single responsibility.
- Avoid excessively long functions and duplicated logic.
- Use standard-library functionality whenever practical.
- Avoid unnecessary global state and circular imports.
- Avoid wildcard imports.
- Keep module-level side effects to a minimum.

### Type Annotations

Type annotations are expected throughout the codebase.

- Annotate function parameters and return types.
- Use appropriate collection and union types.
- Avoid `Any` unless genuinely necessary.
- Prefer precise types over loosely typed interfaces.
- Use `TypedDict`, `Protocol`, `Enum`, or Pydantic models when they provide meaningful value.

```python
def get_system_information() -> dict[str, str]:
    return {
        "platform": "Linux",
        "architecture": "x86_64",
    }
```

### Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Variables | `snake_case` | `system_info` |
| Functions | `snake_case` | `get_system_info()` |
| Classes | `PascalCase` | `SystemManager` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_TIMEOUT` |
| Modules | `snake_case` | `package_manager.py` |
| Private members | Leading underscore | `_validate_config()` |

### Documentation

- Write descriptive docstrings for public functions, classes, and modules.
- Explain non-obvious behavior and important side effects.
- Document parameters, return values, and relevant exceptions.
- Avoid comments that merely repeat the implementation.
- Keep documentation synchronized with code changes.

Use Google-style docstrings consistently.

```python
def install_package(package_name: str) -> bool:
    """Install a system package.

    Args:
        package_name: Name of the package to install.

    Returns:
        True if installation succeeds, otherwise False.

    Raises:
        ValueError: If the package name is invalid.
    """
    return True
```

---

## 5. CLI Architecture and User Experience

Omarchy Tweaker is primarily a terminal application. All CLI development must maintain a consistent and predictable user experience.

### Typer

Use Typer for:

- Application entry points.
- Command and subcommand definitions.
- CLI arguments and options.
- Help messages.
- Input validation.

As the application grows, keep command definitions separate from underlying business logic. Commands should delegate work to appropriate modules rather than contain extensive implementation logic themselves.

### Rich

Use Rich for terminal presentation, including:

- Console output.
- Panels and tables.
- Syntax highlighting.
- Progress indicators.
- Styled messages.
- Logging presentation and tracebacks.

Use consistent formatting throughout the application. Avoid excessive colors, decorative elements, and unnecessary output.

### InquirerPy and Prompt Toolkit

Use InquirerPy for interactive selection and prompt workflows.

Use Prompt Toolkit when more advanced terminal input handling is required.

Avoid implementing custom terminal input systems when existing dependencies already provide the required functionality. Do not introduce overlapping interactive interfaces without a clear reason.

### CLI Design Principles

- Provide clear command descriptions and useful `--help` output.
- Use meaningful command names.
- Validate user input before executing operations.
- Display actionable error messages.
- Avoid unnecessary diagnostic output during normal operation.
- Provide detailed diagnostic information when debugging is appropriate.
- Keep interactive and non-interactive execution predictable.
- Consider terminal compatibility and non-TTY execution.

---

## 6. System Operations and Safety

This application interacts with the host operating system. System-level operations must be implemented carefully.

### Command Execution

Prefer Python's `subprocess` module for executing external commands.

Requirements:

- Use argument lists instead of shell command strings.
- Avoid `shell=True` unless there is a documented and compelling reason.
- Validate user-controlled arguments.
- Use appropriate timeouts for operations that may hang.
- Capture output when needed.
- Handle non-zero exit codes explicitly.
- Avoid silently ignoring command failures.

```python
import subprocess


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Execute a system command safely."""
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
```

Do not blindly execute arbitrary commands assembled from user input.

### Privilege Management

- Do not run the entire application as root.
- Request elevated privileges only for operations that require them.
- Use `sudo` for individual privileged commands when appropriate.
- Never assume the application has administrative privileges.
- Detect and communicate permission failures clearly.
- Do not attempt to bypass system security mechanisms.
- Do not run the application as root; instead provide a clear warning and exit.

### Destructive Operations

Operations that can modify or remove system resources require additional safeguards.

Examples include:

- Removing packages.
- Deleting configuration files.
- Modifying boot settings.
- Changing system services.
- Overwriting user configurations.
- Modifying system directories.
- Changing networking or security settings.

Before performing destructive operations:

1. Validate the target.
2. Explain the intended operation.
3. Request confirmation where appropriate.
4. Preserve existing configuration when possible.
5. Create backups before overwriting important files.
6. Handle partial failures.
7. Report the outcome accurately.

Never silently perform destructive operations.

### Configuration Management

When modifying configuration files:

- Preserve existing settings whenever possible.
- Avoid unnecessary overwrites.
- Prefer targeted modifications.
- Validate generated configuration before applying it when possible.
- Preserve file permissions and ownership where appropriate.
- Create backups before modifying important existing files.
- Make operations idempotent whenever practical.

An operation should ideally produce the same final state when executed multiple times.

---

## 7. Error Handling and Logging

Error handling must be explicit, predictable, and informative.

### Exception Handling

- Catch specific exceptions whenever possible.
- Avoid broad `except Exception` blocks unless they serve a clear application-level purpose.
- Never silently swallow exceptions.
- Do not use exceptions as ordinary control flow.
- Raise meaningful exceptions for invalid application states.
- Preserve the original exception when re-raising or translating errors.

### Logging

Use Python's standard `logging` module for application logging. Rich may be used to improve log and traceback presentation.

| Level | Usage |
|---|---|
| DEBUG | Detailed diagnostic information |
| INFO | Normal application events |
| WARNING | Recoverable issues |
| ERROR | Operations that failed |
| CRITICAL | Serious application failures |

Additional presentation concerns:

- Use Rich progress indicators for long-running operations.
- Render tracebacks for debugging contexts.
- Avoid mixing diagnostic logging with ordinary user-facing output unnecessarily.

Never log passwords, authentication tokens, private keys, sensitive personal information, or confidential configuration values.

### Tracebacks

During development, provide useful tracebacks.

Do not expose unnecessary internal details to ordinary users in production mode. Diagnostic output should help identify the failing operation and provide enough context to troubleshoot it.

---

## 8. Configuration and Data Validation

Use Pydantic for structured configuration and data validation where appropriate.

Requirements:

- Define explicit configuration schemas.
- Validate external input.
- Provide sensible defaults.
- Reject invalid configuration values.
- Keep configuration loading separate from business logic.
- Avoid hardcoding user-specific paths throughout the codebase.
- Use appropriate XDG directories for user-level application data and configuration.

Prefer `pathlib.Path` over manual path manipulation.

Configuration should be easy to inspect, maintain, and migrate as the application evolves. Do not introduce a complex configuration framework unless the application requires it.

---

## 9. Testing Standards

Pytest is the project's testing framework. Every meaningful feature should include appropriate tests.

### Testing Requirements

- Test public functionality.
- Test expected behavior and invalid input.
- Test error conditions and edge cases.
- Mock external commands and system interactions.
- Avoid modifying the real host system during tests.
- Keep tests independent and reproducible.

### Mocking

Use Pytest-Mock for mocking external dependencies.

Functionality that should generally be mocked includes:

- `subprocess` calls.
- Package manager operations.
- Privileged commands.
- Filesystem modifications.
- System service operations.
- External processes.

Tests must never accidentally install or remove actual packages on the developer's machine.

### Test Naming

Use descriptive test names.

```python
def test_install_package_returns_true_on_success() -> None:
    pass


def test_install_package_handles_command_failure() -> None:
    pass


def test_install_package_rejects_empty_package_name() -> None:
    pass
```

### Coverage

Use Pytest-Cov to monitor test coverage.

Coverage is an indicator of test completeness, not a substitute for meaningful assertions. Prioritize critical functionality and failure paths over achieving an arbitrary coverage percentage.

---

## 10. Code Quality and Static Analysis

The project uses Ruff and Mypy.

### Ruff

Ruff is responsible for linting and formatting.

Configured lint rule families:

- `E`: pycodestyle errors
- `F`: Pyflakes
- `I`: import sorting
- `UP`: Python modernization
- `B`: Bugbear
- `SIM`: simplification
- `PERF`: performance

Follow the configuration in `pyproject.toml`.

Do not add inline suppressions merely to silence warnings. Any necessary suppression should have a clear justification.

Ruff also formats embedded Python code blocks in Markdown. Keep Python examples in this file formatted according to Ruff's rules.

### Mypy

Mypy runs in strict mode.

- Maintain complete type annotations.
- Avoid unnecessary type ignores.
- Resolve type errors instead of bypassing them.
- Keep third-party typing limitations isolated.
- Do not weaken the project's strict configuration simply to make existing code pass.

---

## 11. Dependency Management

Use `uv` for project dependency management and execution.

Do not use `pip` directly to manage project dependencies.

### Adding Dependencies

Runtime dependency:

```bash
uv add package-name
```

Development dependency:

```bash
uv add --group dev package-name
```

Documentation dependency:

```bash
uv add --group docs package-name
```

### Removing Dependencies

```bash
uv remove package-name
```

### Synchronizing

```bash
uv sync
```

Install all dependency groups:

```bash
uv sync --all-groups
```

### Lockfile

- Keep `uv.lock` synchronized with `pyproject.toml`.
- Do not manually edit the lockfile.
- Do not remove or replace it unnecessarily.
- Commit lockfile changes when dependency changes require them.

Do not add dependencies without considering their maintenance status, compatibility, and actual necessity.

---

## 12. Development Commands

All development tasks are managed through Poe the Poet.

Run tasks using:

```bash
uv run poe <task>
```

### Code Quality

| Command | Purpose |
|---|---|
| `uv run poe lint` | Run Ruff lint checks |
| `uv run poe lint-fix` | Automatically fix supported lint issues |
| `uv run poe format` | Format Python files |
| `uv run poe format-check` | Check formatting without modifying files |
| `uv run poe typecheck` | Run Mypy |

### Testing

| Command | Purpose |
|---|---|
| `uv run poe test` | Run the test suite |
| `uv run poe coverage` | Run tests with coverage reporting |

### Changelog and Release Notes

| Command | Purpose |
|---|---|
| `uv run poe changelog` | Generate a changelog from Git commit history |
| `uv run poe release-notes` | Generate release notes from Git commit history |
| `uv run poe changelog-preview` | Preview the changelog before generating it |
| `uv run poe release-notes-preview` | Preview release notes before generating it |
| `uv run poe docs-generate` | Generate changelog and release notes for docs |

### Documentation

| Command | Purpose |
|---|---|
| `uv run poe docs` | Generate the Zensical documentation and start the server |
| `uv run poe docs-serve` | Serve the generated documentation locally |
| `uv run poe docs-build` | Build the documentation site |
| `uv run poe docs-compile` | Compile the documentation site for deployment |
| `uv run poe docs-deploy` | Deploy the compiled documentation site |
| `uv run poe docs-publish` | Build and deploy the documentation site |

### Building

```bash
uv run poe build
```

Builds the source distribution and wheel.

### Cleanup

```bash
uv run poe clean
```

Removes generated build artifacts and coverage data.

### Combined Checks

| Command | Purpose |
|---|---|
| `uv run poe check` | Run linting, formatting checks, type checking, and tests |
| `uv run poe pre-commit` | Run essential pre-commit checks |
| `uv run poe ci` | Run the complete quality pipeline |

---

## 13. Documentation Standards

Zensical is used to generate the project's documentation website.

Documentation should be:

- Clear and technically accurate.
- Consistent with the actual implementation.
- Organized into logical sections.
- Easy to navigate.
- Free of outdated instructions.
- Useful to both developers and end users.

### Documentation Changes

Whenever a feature changes:

- Update relevant documentation.
- Update CLI usage examples if necessary.
- Document new dependencies when introduced.
- Explain important system requirements.
- Document potentially destructive behavior.
- Update the changelog when appropriate.

Do not document functionality that has not been implemented.

Use Markdown consistently and follow the existing Zensical configuration.

---

## 14. Git, Versioning and Release

Follow a clean and maintainable Git workflow.

### Commit Messages

Prefer Conventional Commits.

Examples:

```text
feat: add package management commands
fix: handle missing configuration files
refactor: separate system operations from CLI
docs: improve installation documentation
test: add package manager tests
chore: update development dependencies
```

### Versioning

- The project uses Semantic Versioning (`MAJOR.MINOR.PATCH`).
- The version in `pyproject.toml` is the single source of truth.
- Release tags are formatted as `vX.Y.Z` and must match the `pyproject.toml` version.
- The release workflow enforces this match.

### Changelog

Use Git Cliff to generate changelogs.

Keep commit messages descriptive enough to support meaningful automated changelog generation.

### Repository Hygiene

- Do not commit virtual environments.
- Do not commit generated build artifacts.
- Do not commit temporary files.
- Do not commit secrets or credentials.
- Do not commit machine-specific configuration unless intentionally required.
- Keep `.gitignore` updated.

Avoid modifying unrelated files during feature development.

---

## 15. AI Agent Instructions

AI coding agents working on this repository must follow these instructions.

### Before Making Changes

1. Read this `AGENTS.md` file.
2. Inspect the existing project structure.
3. Read `pyproject.toml` before changing dependencies or tooling.
4. Understand the existing implementation before modifying it.
5. Check for existing utilities and reusable functionality.
6. Identify potential system-level side effects.

Do not assume that suggested future architecture has already been implemented.

### While Making Changes

- Follow the existing coding conventions.
- Prefer small, focused changes.
- Reuse existing functionality.
- Avoid unnecessary dependencies.
- Preserve existing public interfaces unless a change is required.
- Maintain strict type checking.
- Write tests for new functionality.
- Update documentation when necessary.
- Never introduce unrelated refactoring.
- Never silently change application behavior.

### System Safety

Agents must be particularly careful when working with operations that affect the host operating system.

Never execute destructive system commands simply to verify an implementation.

Do not:

- Remove packages from the developer's machine.
- Modify bootloader configurations.
- Change system services.
- Overwrite user configurations.
- Change permissions recursively.
- Execute privileged commands without explicit authorization.
- Push anything to the repository without explicit authorization.
- Create any new branches in the repository without explicit authorization.

Use mocks, temporary directories, and isolated test environments whenever possible.

### Before Completing a Task

Run the relevant checks. At minimum, when practical:

```bash
uv run poe check
```

For changes affecting packaging, documentation, or the complete development pipeline, also consider:

```bash
uv run poe ci
```

If a check cannot be completed, clearly explain why.

Never claim that tests, linting, type checking, or builds passed unless they were actually executed successfully.

### Final Response

When completing development work, provide:

1. A concise summary of the changes.
2. The important files created or modified.
3. Any architectural or implementation decisions.
4. Tests and validation performed.
5. Any remaining issues or limitations.
6. Any additional context or information that may be relevant.
7. Suggestions for next steps or improvements.
8. A suggested commit message (short, long, and Conventional Commit style).
9. Any other relevant information.
10. Any additional notes or comments.

Do not claim to have modified files that were not actually changed.

---

## 16. Scope and Project Boundaries

Omarchy Tweaker is primarily a personal customization toolkit.

Agents should not turn it into a generic Linux administration framework without a clear requirement.

Keep the project focused on:

- Omarchy customization.
- Desktop environment configuration.
- Linux system utilities.
- Package management automation.
- Bootstrap workflows.
- Reusable system management functionality.
- Custom configurations.
- Dotfiles and personal settings.

Avoid introducing:

- Unnecessary graphical interfaces.
- Web application infrastructure.
- Unnecessary background services.
- Excessive abstractions.
- Large frameworks for simple operations.
- Dependencies that significantly increase installation complexity without meaningful benefits.
- Core functionality that is not directly related to Omarchy customization and automation.

The application should remain a lightweight, practical, terminal-first toolkit.

---

## 17. Disclaimer and Operational Responsibility

Omarchy Tweaker can interact directly with system configurations and package management.

All agents must treat system modifications as potentially destructive.

Prefer reversible, transparent, and well-documented operations.

The project is intended primarily for personal use. Compatibility with other Linux distributions or configurations must not be assumed unless explicitly implemented and tested.

---

## 18. Agent Execution Report Standard

AI agents must provide a structured, detailed, and professional execution report in the terminal after completing every development task.

The final report is an essential part of the development workflow. It must clearly communicate what was requested, what was implemented, what changed, how it was validated, and whether anything remains unfinished.

Do not finish a task with a vague response such as "Done", "Fixed", or "Implemented successfully".

### 18.1 General Requirements

All final terminal reports must:

- Use clear and descriptive headings.
- Use bullet points for individual changes and explanations.
- Separate different categories of changes into dedicated sections.
- Use consistent formatting throughout the report.
- Include relevant file paths and command names.
- Explain technical changes rather than simply listing them.
- Distinguish between completed work and unfinished work.
- Report actual execution and testing results.
- Avoid unnecessary repetition and irrelevant information.
- Use Rich formatting when appropriate for terminal presentation.
- Use tables to summarize changes, dependencies, or test results when helpful.
- Use code blocks for command outputs and configuration files.
- Use headings, subheadings, code blocks, tables, bullet points, and structured text.

Do not produce excessively long paragraphs. Prefer structured bullet points.

### 18.2 Required Report Structure

Every completed task should follow this structure.

#### 1. Task Summary

Provide a short overview of the requested task and the work completed.

#### 2. Changes Overview

Provide a high-level breakdown of the changes.

Separate changes into the following categories where applicable:

- **Added:** New files, modules, classes, functions, CLI commands, features, dependencies, configuration options, tests, or documentation.
- **Modified:** Existing files that were updated, changed functions or methods, updated application behavior, refactors, updated dependencies or configuration, updated documentation, or updated tests.
- **Removed:** Deleted files, functions, classes, modules, dependencies, deprecated functionality, removed configuration options, or eliminated redundant code.
- **Renamed or Moved:** Renamed or relocated files and directories, updated import paths, or changed identifiers or public interfaces.

**Git Status**

- List files added, modified, or deleted in the Git repository.

#### 3. Detailed Implementation

Explain the implementation in detail.

For each significant change, explain:

- What was implemented.
- Why it was implemented.
- How it works.
- Which components are involved.
- How it integrates with the existing architecture.
- Any important behavior or edge cases.
- Any relevant design decisions.

#### 4. Filesystem Changes

Provide a clear breakdown of affected files and directories.

#### 5. Technical Details

Document important technical decisions and implementation details.

#### 6. Dependencies and Configuration

Report dependency and configuration changes separately.

If no dependencies or configuration were changed, explicitly state:

`No dependency or configuration changes.`

#### 7. Commands Executed

List important terminal commands executed during the task.

#### 8. Testing and Validation

Provide a separate testing report.

#### 9. Issues, Warnings and Limitations

Report anything that remains unresolved.

If there are no outstanding issues, state:

`No known outstanding issues.`

#### 10. Final Outcome

Conclude with a concise summary of the final state.

Use one of these statuses:

- **COMPLETED:** All requested work was implemented and relevant validation passed.
- **PARTIALLY COMPLETED:** Some requested work remains unfinished.
- **BLOCKED:** The task could not be completed because of an unresolved blocker.
- **COMPLETED WITH WARNINGS:** The implementation is complete, but relevant warnings or limitations remain.

#### 11. Suggested Commit Message

Provide a short message, a long message, and a Conventional Commit style message.

#### 12. Additional Notes

Provide any other relevant information.

### 18.3 Report Template

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    OMARCHY TWEAKER
                   TASK EXECUTION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. TASK SUMMARY
───────────────────────────────────────────────────────────
[Concise explanation of the task and its outcome.]

2. CHANGES OVERVIEW
───────────────────────────────────────────────────────────

ADDED
  • [New functionality, files, modules, or dependencies.]

MODIFIED
  • [Updated functionality, files, or configurations.]

REMOVED
  • [Removed functionality, files, or dependencies.]

RENAMED / MOVED
  • [Renamed or relocated files and modules.]

3. DETAILED IMPLEMENTATION
───────────────────────────────────────────────────────────
[Detailed explanation of what was implemented and how it works.]

4. FILESYSTEM CHANGES
───────────────────────────────────────────────────────────
[Relevant file tree with ADDED, MODIFIED, REMOVED, and RENAMED labels.]

5. TECHNICAL DETAILS
───────────────────────────────────────────────────────────
[Important implementation decisions, APIs, logic, and architecture.]

6. DEPENDENCIES & CONFIGURATION
───────────────────────────────────────────────────────────
[Dependency and configuration changes, or confirmation that none occurred.]

7. COMMANDS EXECUTED
───────────────────────────────────────────────────────────
[Important commands and their actual results.]

8. TESTING & VALIDATION
───────────────────────────────────────────────────────────
  • Ruff:       [PASS / FAIL / NOT RUN]
  • Formatting: [PASS / FAIL / NOT RUN]
  • Mypy:       [PASS / FAIL / NOT RUN]
  • Pytest:     [PASS / FAIL / NOT RUN]
  • Build:      [PASS / FAIL / NOT RUN]

9. ISSUES, WARNINGS & LIMITATIONS
───────────────────────────────────────────────────────────
[Outstanding issues, limitations, or manual actions.]

10. FINAL OUTCOME
───────────────────────────────────────────────────────────
STATUS: [COMPLETED / PARTIALLY COMPLETED / BLOCKED /
         COMPLETED WITH WARNINGS]

[Final explanation of the result.]

11. SUGGESTED COMMIT MESSAGE
───────────────────────────────────────────────────────────
SHORT MESSAGE: [Short summary of changes.]
LONG MESSAGE:  [Detailed summary of changes.]
CONVENTIONAL COMMIT: [Conventional Commit style message.]

12. ADDITIONAL NOTES
───────────────────────────────────────────────────────────
[Additional information or context that may be relevant to the task.]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                     END OF REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 18.4 Report Adaptation

The report template is a standard, not a requirement to generate meaningless sections.

All sections must be included. If a section does not apply, mark it as not applicable rather than deleting it.

Agents must adapt the report to the complexity of the task.

- **Small fixes:** Summarize the task, modified files, implementation, and validation.
- **New features:** Provide the full report, including added files, architecture, technical details, and tests.
- **Refactoring:** Focus on modified, removed, and relocated components, architectural improvements, and regression testing.
- **Dependency updates:** Focus on dependency changes, compatibility, lockfile updates, and validation.
- **Documentation changes:** Focus on added or modified documentation, accuracy, and documentation build results.
- **Bug fixes:** Explain the root cause, the fix, and the tests that prevent recurrence.

The objective is not to produce the longest possible report. The objective is to give the developer a complete and trustworthy understanding of the work.

**Every task must end with a clear, structured, and accurate execution report.**

---

## 19. Final Development Principles

Every contribution should reinforce the following principles:

- Build for maintainability, not unnecessary complexity.
- Prefer standard Python solutions.
- Keep the CLI intuitive and consistent.
- Make system operations safe and predictable.
- Keep dependencies minimal.
- Write typed, documented, testable code.
- Respect the existing architecture.
- Keep documentation accurate.
- Never sacrifice reliability for convenience.

**The ultimate goal is to build a clean, reliable, modular, and efficient Omarchy customization toolkit that makes managing a personal Linux desktop easier without introducing unnecessary complexity or compromising system stability.**

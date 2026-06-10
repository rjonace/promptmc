# Contributing to PromptMC

We welcome contributions! This document outlines the process for contributing to PromptMC.

## The PR Gate

**No PR will be reviewed unless all checks pass locally.** Before opening a pull request, ensure:

```bash
# Run tests
pytest

# Run linting
ruff check .

# Run type checking
mypy src/
```

All three must pass. This is non-negotiable. The CI pipeline will run these checks automatically, and if they fail, the PR will not be reviewed.

## The Scope Guard

PromptMC has a focused scope. Please check [`ROADMAP.md`](ROADMAP.md) before submitting major architectural changes.

**We are explicitly NOT building:**

- 3D visualization web apps or UIs
- Unsupervised reactor design or licensing/safety sign-off
- Replacements for OpenMC's native tools (Plot Explorer, etc.)

**We ARE building:**

- Validation-first workflow acceleration
- MCP server exposing OpenMC tools to AI assistants
- Structured geometry generation with physics guards
- Fail-fast input validation

If you're unsure whether a feature fits the scope, open an issue first to discuss it before writing code.

## Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Ensure all checks pass (`pytest`, `ruff check`, `mypy src/`)
5. Commit your changes (use conventional commit prefixes: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `ci:`, `chore:`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Code Quality Standards

- **Linting**: Ruff with strict rules (80 character line length)
- **Type Checking**: MyPy in strict mode
- **Testing**: pytest with coverage reporting (the bar is the current Codecov number — see the README badge; it must not decrease)
- **Security**: Bandit security scanning
- **Formatting**: Ruff formatter

## Testing

- New features require test coverage
- Tests must pass on Python 3.10, 3.11, 3.12, 3.13, and 3.14
- Integration tests should use real OpenMC runs where possible (see `src/promptmc/examples/uo2_criticality/`)
- Avoid relying solely on unit test mocks for critical paths

## Documentation

- Update documentation for API changes
- Add docstrings to public functions (Google style)
- Update the README if user-visible behavior changes
- Update ROADMAP.md if a roadmap deliverable is completed

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

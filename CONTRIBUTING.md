# Contributing to Open CAN Analyzer

Thank you for helping make CAN analysis more accessible.

## Development setup

1. Fork and clone this repository.
2. Create a virtual environment: `python -m venv .venv`.
3. Activate it and run `python -m pip install -r requirements-dev.txt`.
4. Create a focused branch.
5. Run `python tools/validate_project.py` and
   `python -m unittest discover -s tests -v` before submitting a pull request.

Keep reusable logic in `oca/` and Tkinter-specific code in the GUI entry point. Preserve
protocol v1 compatibility when extending protocol v2. Do not add hardware-specific IDs to
the application; put examples in public JSON profiles instead.

All visible interface text must use translation keys. Add the English key first, add the
Brazilian Portuguese translation and verify that both catalogs have identical key sets.

## Pull requests and reports

Explain the motivation, user-visible behavior, tests and platforms checked. Bug reports
should include the OCA version, operating system, Python version, serial adapter, protocol
version and a minimal sanitized reproduction. Never upload proprietary DBC files, private
captures, credentials or data obtained without permission.

By contributing, you agree that your contribution is licensed under the MIT License and
that you will follow the project Code of Conduct.

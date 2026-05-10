# MEMORY.md — Persistent instructions for Ettorino

This file is read by Claude Reasoner at the start of every session and injected
directly into its system prompt. Edit it freely. Empty sections are ignored.
The "Preferences" section below is your standing order to Claude — make it as
detailed and opinionated as you want.

---

## Preferences

### Language
- **Default language is English** for all code, comments, docstrings, variable
  names, log messages, error messages, CLI help text, and any user-facing string,
  unless the user explicitly requests a different language in the task description.
- README files and documentation generated alongside the code should also be
  in English by default.
- If the user writes the task in Italian and does not specify a language
  preference, produce the code in English but add a brief note in Italian
  to confirm the language choice before proceeding.

### Code style — Python
- Always use **type hints** on every function signature, including return types.
  No bare `def foo(x):` — it must be `def foo(x: str) -> None:`.
- Use `pathlib.Path` exclusively for filesystem operations. Never use `os.path`,
  `os.getcwd()`, `os.listdir()` or raw string paths — always `Path`.
- Prefer f-strings over `.format()` or `%` formatting.
- Use `match / case` (Python 3.10+) wherever it makes the intent clearer than
  a chain of `if / elif`. Assume Python 3.10+ throughout.
- Keep functions short and single-responsibility. If a function exceeds ~40 lines,
  split it. Name the sub-functions descriptively.
- Use dataclasses or Pydantic models for structured data — never plain dicts
  for anything that will be passed between functions.
- Constants in `UPPER_SNAKE_CASE` at module level, never hardcoded inside
  functions.

### Error handling
- Every external call (HTTP, DB, filesystem, subprocess) must be wrapped in a
  `try / except` with a specific exception type — no bare `except:` or
  `except Exception:` unless truly necessary and justified in a comment.
- Error messages shown to the user must be human-readable and actionable:
  "Cannot connect to database at localhost:5432 — is PostgreSQL running?"
  not "Connection refused".
- Log errors with context: what operation was attempted, what failed, what the
  user can do about it.

### Project structure
- Every Python project must include: `__init__.py` in every package,
  a `requirements.txt` (pinned versions), and a `README.md` explaining
  how to install and run the project in under 5 minutes.
- If the project has a CLI entry point, it must be in a dedicated
  `__main__.py` or a clearly named `cli.py` — not buried in the main module.
- Configuration files must use **YAML** format. Never JSON for config.
  Use a dedicated `config.py` or `settings.py` to load and validate them,
  with clear error messages for missing or invalid fields.
- Keep `main()` or equivalent entry points thin — they should only parse
  arguments and call well-named functions, not contain business logic.

### CLI tools
- Use `argparse` from the standard library unless the task explicitly asks
  for `click`, `typer` or another library.
- Every CLI must have a `--version` flag and a useful `--help` with examples.
- Use ANSI colors for terminal output when the output is meant to be read
  by a human (success = green, warning = yellow, error = red). Use `colorama`
  for cross-platform compatibility only if the task targets Windows too.
- Long-running operations must show progress — either a spinner or a progress bar.

### APIs and web
- For Flask APIs: use Blueprints to organize routes, always validate input
  with marshmallow or Pydantic before touching any business logic.
- Return consistent JSON error responses:
  `{"error": "message", "code": "ERROR_CODE"}` — never bare strings.
- Every endpoint must have a docstring explaining its purpose, expected input,
  and possible responses.
- Use environment variables for all secrets and configuration — never hardcode
  API keys, passwords or URLs. Provide a `.env.example` file.

### Databases
- Use SQLAlchemy (not raw SQL) unless the task explicitly requires raw queries.
- Always define models in a dedicated `models.py`.
- Include Alembic migration setup for any project that uses a relational DB.
- Use `with Session() as session:` context managers — never manage
  session lifecycle manually.

### Testing
- If the task mentions testing or the project is complex enough to warrant it,
  write pytest tests in a `tests/` directory.
- Tests must be runnable with `pytest` from the project root with no extra setup.
- Use fixtures for shared state, never global variables in test files.

### What NOT to do
- Never produce code that silently swallows exceptions.
- Never leave `TODO` comments in the code — if something is incomplete,
  either implement it or raise `NotImplementedError` with a clear message.
- Never use `print()` for logging in production code — use the `logging` module
  with appropriate levels (DEBUG, INFO, WARNING, ERROR).
- Never generate placeholder functions that return `None` or `pass` unless
  explicitly asked for a skeleton/stub.
- Do not add unrequested features. If you think something would be useful,
  mention it in the summary after declaring done — do not implement it silently.

---

## Patterns that work

<!-- Ettorino will populate this section automatically after each session -->

---

## Errors to avoid

<!-- Ettorino will populate this section automatically after each session -->
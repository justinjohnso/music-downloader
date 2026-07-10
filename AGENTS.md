# Music Downloader Agent Instructions

## Global AI Conventions & Skills (Environment Integration)
**NEGATIVE CONSTRAINT**: NEVER execute `edit`, `multiedit`, `write`, or complex `bash` commands without first using the `view` tool to read the relevant `SKILL.md` from `~/.config/ai/skills/` or `~/.config/crush/skills/`.
If you are unsure which skill applies, you MUST load `coding-standards` or `systematic-debugging` before acting.
*This project assumes developers may have local AI conventions (e.g., in `~/.config/ai/`). Agents must check for and respect local environment rules before overriding project defaults.*

You are Gemini CLI / Claude / Cursor, assisting with the `music-downloader` project. This file serves as the shared context for all AI agents working on this codebase.

## Project Mission
A robust Python-based tool for downloading high-quality music tracks from Deezer (with Qobuz fallback) using search queries or Spotify links. The tool aims to be simple, fast, and highly configurable.

## Tech Stack
- **Language**: Python 3.10+
- **UI**: PyQt6 (GUI)
- **Core Engine**: streamrip (Vendored in `vendor/streamrip`)
- **APIs**: spotipy (Spotify metadata), deezer-py
- **Config**: tomlkit (preserves comments), appdirs (resolves paths)
- **Tooling**: ruff (linting/formatting), pytest (testing), setuptools (build via `pyproject.toml`)

## Project Structure & Architecture
- `src/downloader.py`: CLI entry point (`mdl`, `mdl-gui`, `--setup`, `--sync-db`, `--set-arl`). Handles flag parsing and async task execution.
- `src/core.py`: Main download orchestration. Wraps `streamrip` functionality (like `DeezerClient`, `PendingTrack`, `Database`) and manages downloads (including duplicate track resolution: prompt, skip, redownload).
- `src/config.py`: Global config management, streamrip schema validation, and **critical monkey-patches** applied at runtime to vendor logic.
- `src/gui.py`: PyQt6 GUI implementation.
- `src/spotify.py`: Spotify link parsing and metadata extraction using `spotipy`.
- `src/schema.py`: Configuration schema definitions.
- `tests/`: Extensive `pytest` suite ensuring config stability (`test_auto_repair.py`, `test_schema_drift.py`, `test_set_arl.py`, etc.).
- `vendor/streamrip`: Submodule containing the core engine. Do not modify directly unless patching behavior.

## Configuration and Global Behavior (Gotchas)
- **Config Path Resolution**: `mdl` searches for `mdl-config.toml` in the following order: Platform App Support > User Home > CWD.
- **Submodule Pathing**: `src/__init__.py` injects `vendor/streamrip` into `sys.path`.
- **Safe Mode**: Logic in `src/config.py` (`is_streamrip_config_customized()`) prevents overwriting user-customized `streamrip` configs on disk, applying them in-memory only.
- **Monkey-patching (DO NOT REMOVE)**: `src/config.py` explicitly monkey-patches `streamrip.config.ConfigData.from_toml` at runtime to auto-upgrade config versions and inject strictly required `deezer` fields (like `lower_quality_if_not_available`, `use_deezloader`) without crashing. It also patches `streamrip.progress.ProgressManager` to inject a custom Rich layout (cyan/green color scheme).
- **SQLite Tilde Bug**: `sqlite3` does not expand `~` automatically. All database paths inside configurations MUST be expanded via `os.path.expanduser` before handing them to `streamrip`. Treat any tilde-prefixed db path as "needs repair".

## Executable Commands
| Action | Command |
| :--- | :--- |
| Run CLI | `python3 -m src.downloader` or `mdl` |
| Run GUI | `python3 -m src.downloader --gui` or `mdl-gui` |
| Setup Wizard | `mdl --setup` |
| Set ARL | `mdl --set-arl` |
| Sync DB | `mdl --sync-db [PATH]` |
| Run Tests | `pytest -ra` |
| Lint Check | `ruff check .` |
| Format Code | `ruff format .` |
| Install | `pipx install .` |

## Tool Preferences: X-First Conventions
Refer to the local AI environment for these mandatory behaviors (`~/.config/ai/conventions/x-first-conventions.md`):
- **Context7-first**: Use `context7_*` MCP tools before web search for any library/framework/SDK documentation.
- **Time-first**: Use `time_*` MCP tools for current date / timezone conversion instead of guessing or using `date`.
- **Memory-first**: Use `memory_search_nodes` before asking the user for clarifying questions.

## Code Style and Conventions
- **Naming**: PEP 8 (snake_case for variables/functions, PascalCase for classes).
- **Formatting**: Use `ruff format` (Black compatible).
- **Typing**: Use type hints for all function signatures and complex variables.
- **Documentation**: Google-style docstrings for all public methods and classes.
- **Linting**: Address all `ruff` findings before finishing. No `noqa` unless absolutely necessary.
- **Auth Errors**: Catch exceptions explicitly. `streamrip.exceptions.AuthenticationError` is often raised bare (empty `str(e)`); surface a hand-written message pointing users to `--set-arl` or `--setup`.

## Boundaries and Security
- **Never Touch**: `.git/`, `__pycache__/`, `build/`, `dist/`.
- **Submodule Changes**: Be careful when updating `vendor/streamrip`. Prefer monkey-patching in `src/config.py` over direct edits to the submodule.
- **Secrets**: Never log or commit ARLs, tokens, or credentials. Use `mdl-config.toml` (ignored by git).
- **Git**: NEVER push changes to a remote or run `git commit` without an explicit instruction from the user. Default to staging changes only and suggesting a message. **Commit messages**: lowercase, direct, descriptive — no conventional prefixes (feat:, fix:, chore:, etc).

## Config Wizard Invariants & Gotchas
These rules exist because partial configs silently crash streamrip with cryptic errors. Do not regress them.

1. **Emit the full streamrip schema.** `--setup` must write all 15 streamrip sections, not just the few mdl cares about. Use `tomlkit` so user comments/values survive re-runs.
2. **Idempotent setup.** Re-running `--setup` must preserve every user-set value and only fill missing keys. Never overwrite a populated key without an explicit advanced-options prompt.
3. **Auto-repair on every startup.** `ensure_mdl_config_complete()` runs silently at CLI entry and fills any missing/empty keys against the current streamrip schema, corrects legacy naming (e.g. `[conversions]` to `[conversion]`), and expands unexpanded `~` database paths. This is the safety net for users whose configs predate a schema update.
4. **Credential files get `chmod 600`** and a banner warning at the top. Applies to `mdl-config.toml` and any file containing ARLs/tokens (`_secure_write`).
5. **Strict ARL validation.** `--set-arl` must do a live login round-trip before writing; never persist an unvalidated ARL. Update both `mdl-config.toml` and streamrip's `config.toml` in the same call.
6. **Catch auth errors in download paths.** `streamrip.exceptions.AuthenticationError` is often raised bare (empty `str(e)`); surface a hand-written message that points at `--set-arl` / `--setup` (handled in `download_multiple_tracks`).

## Verification Checklist
Before declaring a task "done," ensure:
1. All changes follow the defined Code Style.
2. `ruff check .` and `ruff format .` have been executed.
3. Behavior has been verified via the CLI or GUI.
4. `pytest` passes (tests live in `tests/`, checking schema drift, auto-repair, config setup).
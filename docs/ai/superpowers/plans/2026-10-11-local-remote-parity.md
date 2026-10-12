# Local and remote parity implementation plan

## Goal and scope

Preserve the installed application behavior and integrate remote security fixes without changing the installed application or user config.
Work on `sync-local-and-remote`, based on remote `372d0e5`, in an isolated worktree.
Keep local `main` at `1282365`. Do not rewrite history, modify vendored sources, deploy a backend, or replace user credentials.
Commits require an explicit commit instruction. Publication, merge approval, and release tagging remain separate gates.

## Approach

An integration branch preserves both histories and excludes unfinished experiments.
Replacing remote files with local files would discard security fixes.
Merging experimental branches would introduce unrelated config and backend changes.

## 1. Preserve and integrate

Merge local `main` with `--no-commit --no-ff` into the integration branch.
Keep remote requirements and CODEOWNERS. Preserve the three local fixes and their existing quality-mapping test.
Run the existing pytest suite after integration. Keep the original checkout, installed package, and four stashes unchanged.

## 2. Regression coverage

Extend `tests/test_spotify.py` with public playlists, private playlists, metadata and first-page authentication failures, pagination, empty playlists, unavailable tracks, and non-authentication errors.
Use deterministic Spotify client doubles. Check returned tracks and which authentication client handles pagination.
Use typed Spotify status codes instead of substring checks. Restart playlist retrieval with user authentication if app authentication fails during pagination, without duplicate tracks.
Extend `tests/test_streamrip_integration.py` with the existing quality mapping and fallback boundary verification using the actual vendored client with network calls replaced.
Record failures on the remote baseline for existing fixes and RED/GREEN evidence for new behavior.

## 3. Clean installation and CI

Modify `requirements.txt` and `pyproject.toml` only where clean-install verification identifies compatibility gaps.
Declare PyQt6, retain secure Pillow, preserve the Python 3.10 support floor, and align pytest plugins with pytest 9.
Scope setuptools discovery to the application and required vendored packages. Include the vendored config template.
Keep vendored code read-only and exclude it from application Ruff checks.
Add `.github/workflows/application-ci.yml`: recursive checkout, fresh install, dependency check, pytest, CLI help, and offscreen GUI smoke.
Cover Linux, macOS, and Windows with Python 3.10 and a current Python version. Run lint and formatting in one job.
Validate PR #7's urllib3 update in an isolated environment. Keep its merge separate from application parity.
Build wheels outside project roots and exercise installed entrypoints from outside the source checkout.

## 4. Branch and stash cleanup

Delete only the fully merged local `interactive-search` branch with Git's safe deletion mode.
Delete remote `add-codeowners-1786194555` only after verifying its exact tip is an ancestor of current remote main.
Preserve unmerged experiment branches and all stashes. Record their tips and salvage recommendations in `docs/maintenance.md`.
Do not force-delete unmerged work or apply historical stashes over current code.

## 5. Acceptance and release gates

Run pytest, `ruff check .`, `ruff format --check .`, installed CLI help, an offscreen GUI smoke, wheel install, and dependency checks.
Review the complete staged, unstaged, and untracked candidate. Confirm local main and the installed app remain unchanged.
Do not claim CI matrix or live downloads pass without executed evidence.
Prepare a parity PR only after an explicit commit instruction. Respect the required approval and CodeQL gates.
After reviewed PRs merge, tag a release and update the local installation only with authorization.

## Testing decisions

Selected: unit tests for playlist decisions; integration tests for config and vendor boundaries; installed-entrypoint and GUI smoke tests.
Rejected: hosted-backend contract tests, performance tests, and a new property-testing dependency. These changes do not introduce those surfaces.
Live authenticated downloads are not automated because they need private credentials and create downloaded files.

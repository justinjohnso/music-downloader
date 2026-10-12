# Maintenance and release gates

## Integration candidate

The `sync-local-and-remote` branch integrates remote security updates with local `1282365`.
The merge preserves remote security pins and local Spotify and quality fixes.
The original checkout and installed application remain unchanged.

The candidate adds playlist pagination authentication coverage, typed error handling, quality fallback checks, PyQt6 dependencies, and application CI.
Setuptools packages only the application and bundled streamrip modules. Fresh installations do not need a separate streamrip distribution.
A separately installed streamrip distribution can still report its own Pillow conflict. Do not downgrade Pillow to hide that unrelated metadata conflict.

## Verification

- Remote source baseline: 23 existing tests passed.
- Local source baseline: 24 existing tests passed.
- Candidate: 44 tests passed on macOS with Python 3.12 and 3.14.
- Original remote code: nine failures with the candidate playlist and quality regression tests.
- New pagination/status handling: five failures before the change, then all playlist tests passed.
- Fresh wheel: installed CLI help, config template, and offscreen GUI smoke passed outside the checkout.
- Ruff lint and formatting checks passed. Vendored code remains unchanged.
- Python 3.10 dependency resolution passed. The Linux/Windows/Python 3.10 CI executions remain unverified until publication.

## Dependency PR

PR #7 merged into remote main at `4442b80`. It changes only urllib3 from 2.7.0 to 2.8.0.
The candidate's 44 tests passed with 2.8.0 in an isolated environment. Its dependency check passed after removal of stale installed application metadata.
The 2.8.0 environment audit reported no known dependency vulnerabilities.
The 2.7.0 environment audit reported three urllib3 advisories, all fixed by 2.8.0.

The release changes HTTPS proxy certificate handling. Users with custom HTTPS proxies need to review their proxy TLS config.
The parity branch includes the merged dependency update. Dependency and application changes retain separate review history.

## Branch cleanup

The merged local `interactive-search` branch (`02bf890`) and remote `add-codeowners-1786194555` branch (`27ca2cf`) were deleted after ancestry checks.
Their commits remain reachable from main.

Preserve these unmerged branches:

| Branch | Local tip | Remote tip | Disposition |
| --- | --- | --- | --- |
| cli-updates | 5c9a940 | d879285 | Review interactive CLI work separately. Do not replace current config code with this historical branch. |
| gui-visual-updates | c5d4e28 | None | Salvage GUI presentation separately. This branch also carries historical backend changes. |
| remote-spotify-resolver | 26316ce | Deleted upstream; cached tip 7afbdad | Preserve the local branch. Treat the cached remote reference as historical. |
| pre-launch-updates | None | 691602a | Review documentation and search changes separately. Config deletions are incompatible with current invariants. |
| spotify-auth-backend | None | f4161ef | Preserve as an unfinished backend experiment. Closed PR #5 does not mean this branch is merged. |

Remote branch age is not evidence that unmerged work is disposable.
Before deletion, archive exact tips or create focused salvage PRs. Do not bulk-merge these branches.

Four stashes remain unchanged:

- `stash@{0}`: gitignore changes.
- `stash@{1}`: gitignore and example config changes.
- `stash@{2}`: gitignore and agent instructions.
- `stash@{3}`: README and a large historical CLI deletion.

Review stashes in isolation. Do not apply them over the integration candidate or delete them based on age.

## Publication and release

1. Commit the reviewed integration candidate after authorization.
2. Publish the integration branch and open a PR after authorization. Do not push directly to main.
3. Let Application CI and CodeQL run. Obtain the required approval without a protection bypass.
4. Verify authenticated public/private playlists and actual MP3/FLAC output with approved credentials and a temporary download directory.
5. Merge the reviewed dependency and parity changes. Tag a tested release with a distinct version after release authorization.
6. Update the local checkout and pipx installation only after merge and authorization.

Keep config paths, custom config values, and download databases unchanged.
Keep the previous release available for rollback. A green mock test does not prove a live Spotify or Deezer request succeeds.

An independent review found an existing limitation: `--setup` and `--set-arl` merge mdl values into streamrip without the customized-config safeguard.
The parity candidate does not introduce or change this behavior. Users with independently customized streamrip configs need a backup before these commands.
Do not use either command as an upgrade step. Repairing this separate config behavior needs focused preservation tests before a change.
The review also found a Windows snapshot fixture mismatch. The candidate uses a POSIX fixture path for the POSIX snapshot, without weakening comparisons.

## Sources

- Bundled streamrip revision: `095ec9fe0c1662b32b42e202d86dbc0159a94abf`.
- pytest-asyncio 1.4.0 release and pytest compatibility: https://github.com/pytest-dev/pytest-asyncio/releases/tag/v1.4.0
- urllib3 2.8.0 security and proxy changes: https://github.com/urllib3/urllib3/releases/tag/2.8.0

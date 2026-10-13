# Historical experiment salvage audit

Baseline: remote main `08197ce`. Final pass inspected seven old local/remote branch refs, 51 unique commits outside main, and 73 distinct Python source snapshots. All four stash working trees, index parents, and untracked parents were checked. No branch, stash, installed app, or user config was deleted or replaced.

## Missed work found

- CLI: stash `ed598e1` contains `-c/--config` forwarding to an explicit streamrip config. Added to the CLI PR with current session overrides and preservation rules. The stash's imports and orchestration are obsolete and were not copied.
- GUI: recursive artist/album selection, queue deduplication, retry/rematch, explicit markers and formatted duration, status/progress widgets, a collapsible log view, version display, config help, and immediate Spotify batch queueing are useful requirements not fully covered by the first draft. Keep them in the GUI PR.
- GUI: native setup with folder browsing and quality choices is already being salvaged with validation/private writes. Do not copy the historical unvalidated config overwrite.
- Playlist: actual final output paths, all supported audio formats, and batch-only playlist contents remain assigned to the playlist PR. Use resolved engine paths, not title/mtime guessing. Preserve original source order, including duplicate redownloads.
- Cleanup: `mdl.spec` is an obsolete PyInstaller file pointing to missing `main.py` and an absolute machine-specific streamrip config. It has no usable release build workflow. Archive/remove it with cleanup, not the application PRs.

## Branch dispositions

| Work | Source | Disposition |
| --- | --- | --- |
| Candidate normalization, display, selection, result limits, broader-query retry | 95f6852; cli-updates 5c9a940/d879285 | CLI PR; first-result remains default rather than adopting the historical default-interactive change. |
| Session cleanup and actionable credential errors | 2ece509; 8760713 | Current main already retains auth guidance; CLI PR removes cancellation of unrelated tasks. No credential debug output is copied. |
| GUI styling, grouped results, multi-selection, queues, monitoring, rematch, setup, config help | 17ab3c0; 8b15744; 76c6e41; c5d4e28 | GUI PR on CLI search API. Queue identity uses explicit item association, not first-pending/name guessing. |
| Session file tracking/M3U | 8760713; 3301ffb | Playlist PR. The old code sorts away source order and guesses filenames; those implementations are rejected. |
| Config migration, setup, unified schema, path expansion | b603439; 82b23cc; stash ancestor variants | Superseded by reviewed main preservation/schema fixes. No additional missing feature. |
| Backend resolver, schemas, API guard, service/deployment files | f96c6b9; 1336799; 44b9ba3; f4161ef; remote-spotify-resolver | Archive as historical reference. Older branch has a fail-closed guard/consistent contract; newer branch regresses both. No approved hosted-service requirement. |
| Docs, agent instructions, dependency/build declarations | old branch tips and stash ancestors | Current release docs, explicit Git rules, pinned secure dependencies, bundled config/licenses supersede them. Do not import security downgrades or unsupported feature claims. |

## Stashes

| Stash commit | Parents/content | Disposition |
| --- | --- | --- |
| 5e3d4e1 | Cache ignore-pattern edits; empty index diff | Already represented in main. |
| 47fe808 | Cache ignores plus malformed hand-edited example config; empty index diff | Ignores superseded. Example includes literal ellipsis/removes required fields; reject. |
| bd50360 | Removes broad ignore rules; adds explicit Git authorization rule; empty index diff | Git rule already present. Do not remove secret/build ignores. |
| ed598e1 | Historical CLI split, README structure, empty index diff, untracked config/core/Spotify modules | Salvage `--config`. Untracked modules implement old first-result matching and overrides already superseded by main. No extra GUI/backend/search features. |

The untracked stash parent contains exactly `src/config.py`, `src/core.py`, and `src/spotify.py`. Those files must remain included in any recovery bundle.

## Recovery archive

A local recovery bundle is available at `/tmp/music-downloader-experiments-complete-v2.bundle`; Git verified it as complete. It includes old branch tips and explicit refs for all stash commits, including the untracked-parent files. Keep this local artifact private; it is not uploaded in the cleanup PR.

The obsolete patch, helper, patch README, and machine-specific `mdl.spec` are removed by cleanup. Existing branches/stashes remain until salvage PRs are merged and deletion is explicitly authorized. Do not remove them based solely on a pending PR.

## Limits

This was a source/history audit, not runtime acceptance of old branches. Pre-launch/backend share an unterminated f-string in core; application startup is broken at those tips. Old GUI cancellation stops its loop before cleanup, config editing drops values, and backend environment/contracts disagree. Safe salvage requires current tests, not wholesale cherry-picks.

No additional useful CLI or config behavior was found beyond the mapped items. GUI completeness remains open until the listed UI gaps are implemented and tested. Archive decisions do not authorize deployment or history deletion.

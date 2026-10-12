# Config preservation plan

## Scope and policy

Fix writes initiated by setup, ARL refresh, and session overrides. Keep the installed app and real user files unchanged during development.
ARL refresh changes only `deezer.arl` in both config files. Setup updates mdl values explicitly answered by the user, but does not overwrite independently customized streamrip files.
Fresh/default streamrip files can receive setup values. Session overrides stay in memory when the actual target file is customized, including path-only customization.
Do not add ownership markers, migrate credentials to a new storage system, or change the vendored engine.

## Defects

- Setup and ARL refresh call an unrestricted merge that copies unrelated credentials, paths, conversion, and concurrency settings.
- ARL refresh invokes the full mdl schema writer instead of a narrow credential edit.
- The customized-config detector ignores path changes and checks the default path rather than the actual Config target.
- Validation creates a streamrip config before login succeeds.
- Legacy setup writes a fresh schema instead of preserving unknown keys/comments. Declining migration still targets the modern location.
- Advanced defaults come from the schema and can reset existing values on Enter.
- Streamrip merges use ordinary writes. Credential temporary files get restricted permissions only after replacement.
- Auto-repair replaces populated tilde database paths with default locations. Missing database sections can retain empty paths in the setup writer.
- Two-file ARL updates are not a filesystem transaction. Use pre-parsed documents and recover the first file on a second-write failure; do not promise crash-safe multi-file atomicity.

## Implementation

1. Add real-file tests in `tests/test_config_preservation.py` for both config documents, customized paths/comments/unknown keys, malformed files, write failures, and secure temp-file permissions.
2. Use a unique same-directory private temp file, close it before atomic replacement, and remove leftovers on failure.
3. Make customization detection accept the actual file path and preserve path-only customizations. Route merge and session overrides through this policy.
4. Use `Config.defaults()` during credential validation. Set ARL directly after validation, prepare both documents before writes, and recover original mdl contents if the streamrip write fails.
5. Preserve all legacy content when migration is accepted, and respect a declined migration. Seed advanced defaults from current values. Fill required empty database paths without relocating populated paths.
6. Update README and maintenance notes with the exact preservation policy and the multi-file crash-consistency limitation.

## Verification

Use temporary files and fake login only. Run the new regressions RED before fixes, then GREEN. Run full pytest, Ruff, installed-entrypoint smoke, and a read-only review.
No real ARL rotation, setup, config rewrite, commits, pushes, or installation changes without separate authorization.
Selected tests: deterministic unit decisions and filesystem/command integration. No external-service test or new dependency is required.

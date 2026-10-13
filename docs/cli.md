# Command reference

The development CLI uses verbs. Published `0.1.0` retains its older flag interface. `mdl` and `music-downloader` use the same entrypoint; `mdl-gui` launches the GUI directly.

```text
mdl [--verbose] [--config PATH] VERB [ARGUMENTS] [VERB FLAGS]
mdl INPUT
```

Bare input is a shorthand for the existing download behavior, including Spotify resolution, history, and duplicate review. Use `mdl download -- "search"` for a query that matches a reserved verb.

## Commands

| Command | Behavior | Flags |
| --- | --- | --- |
| `mdl download INPUT` | Existing Spotify/query matching and download workflow | `--batch FILE`, `--retries N`, `--retry-failed`, `--json` |
| `mdl search QUERY` | Direct Deezer interactive search; Space selects, Enter authorizes downloads, Escape exits | `--type track\|album`, `--first`, `--output-file PATH`, `--num-results N` |
| `mdl setup` | Existing config wizard | |
| `mdl auth refresh [ARL]` | Validate/update only the Deezer ARL in both configs | Prefer omitting ARL for the masked prompt |
| `mdl library sync [PATH]` | Record matching Deezer IDs from existing audio tags | |
| `mdl gui` | Launch GUI | |
| `mdl --help`, `mdl VERB --help` | Help without config writes or login | |
| `mdl --version` | Package version | |

`-v/--verbose` is accepted before or after the verb. `-c/--config PATH` selects an engine config for download/search; mdl session values still apply. It is not a mdl-config path override. Use one command per invocation.

## Search

```bash
mdl search "glitter jkyl"
mdl search "Rumours" --type album
mdl search "glitter jkyl" --num-results 10
mdl search "glitter jkyl" --first
mdl search "glitter jkyl" --output-file matches.json
```

Search uses the bundled streamrip menu and summaries, not an external `rip` executable. Deezer is implicit; tracks are the default type. Only tracks/albums are exposed. The adapter bounds results even though the pinned upstream interactive implementation ignores its own CLI limit.

`-f/--first` authorizes downloading the first result without a menu. `-o/--output-file` writes upstream-format JSON and never downloads. These modes are mutually exclusive. `-n/--num-results` is a positive result limit, default 100. First mode requests one result.

Interactive search requires terminal input/output. Redirected/headless callers must choose first or export mode. Existing config files are read without upstream CLI initialization or automatic credential prompts; missing/invalid ARL produces setup/refresh guidance.

Search selections use upstream single-track/album media handling. Album folders and source-folder options can differ from mdl's Spotify title-matching path. History still checks Deezer track IDs. Changing destination/quality does not invalidate history.

## Downloads and queues

```bash
mdl "https://open.spotify.com/playlist/PLAYLIST_ID"
mdl download "spotify:album:ALBUM_ID"
mdl download "Artist - Track"
mdl download --batch tracks.txt --retries 1
mdl download "Artist Track" --retry-failed
mdl download "spotify:album:ALBUM_ID" --json
```

Bare and plain `download` preserve the existing first-match behavior. Spotify supplies artist/title metadata, then mdl searches Deezer. It does not guarantee the same recording as the Spotify ID.

`--batch FILE` reads UTF-8 queries or Spotify links, one per nonempty line. Lines starting with `#` are ignored. Batch input and positional input are mutually exclusive.

`--retries N` retries failed queue items 0-10 times, retaining the chosen match. `--retry-failed` offers retry/rematch/skip in a terminal; rematch explicitly chooses a replacement. JSON mode cannot use interactive retry.

`--json` emits per-track `query`, `status`, `message`, `candidate_id`, and `path`. Raw candidate payloads are not emitted. Queue modes skip duplicates without opening duplicate-review prompts. Failures exit 1; Ctrl+C exits 130. Legacy plain downloads can still report failures only in text, so inspect their summaries.

## Maintenance

Setup retains its current prompt defaults, migration, schema, and config-preservation behavior. ARL refresh validates before writing and should use the masked prompt rather than exposing a credential in arguments/history.

Library sync scans lowercase `.mp3`, `.flac`, `.m4a`, and `.ogg` recursively. It requires title/artist tags, tries ISRC when present, otherwise artist/title, and records the first Deezer match. It requires login and enabled download history. Audio files are not modified.

## Compatibility aliases

For one transition, old `--setup`, `--set-arl`, `--sync-db`, and `--gui` keep their existing behavior with deprecation guidance. Legacy `--search` remains read-only listing; it is never silently converted to interactive download. Legacy `--select`, `--first-result`, and `--result-limit` remain isolated compatibility options, not the public verb grammar.

Canonical search needs no `--select`; its menu always waits for consent. There are no mdl equivalents for upstream repair, database browsing, Last.fm, ID, or arbitrary source commands. This release only adapts direct Deezer search.

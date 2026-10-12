# Command reference

Applies to the current development checkout. The published `0.1.0` release does not include the search/selection flags below. `mdl` and `music-downloader` call the same CLI entrypoint. `python -m src.downloader` is equivalent in a configured development environment. `mdl-gui` launches the GUI directly; it does not parse CLI flags.

## Arguments and flags

| Argument | Default | Behavior |
| --- | --- | --- |
| `input` | Omitted | Optional search query or Spotify track/playlist/album URL or URI. Quote queries containing spaces. Without input or an action flag, mdl checks config, repairs it, and prints help. |
| `-h`, `--help` | Off | Print argparse help and exit without config repair, login, or downloads. |
| `-v`, `--verbose` | Off | Additional download/sync diagnostics. With `--set-arl`, include validation error details. Setup and GUI do not use this flag to change their interface. |
| `--gui` | Off | Launch the Download/Config GUI. It bypasses CLI auto-repair. |
| `--setup` | Off | Run the interactive setup wizard, save config, and run repair. It does not download the positional input. |
| `--sync-db [PATH]` | Off | Scan a library and add matched Deezer IDs to download history. Without PATH, use `downloads.folder`. With PATH, use that path instead. No audio download or deletion. |
| `--set-arl [ARL]` | Off | Validate and replace only the Deezer ARL in both configs. Without a value, prompt with masked input. Explicit values can appear in shell history/process arguments; prefer the prompt. |

| `--search` | Off | List Deezer matches without downloading audio. Requires a query. |
| `--select` | Off | Choose a match before each download in an interactive terminal; redirected input keeps first-result behavior. |
| `--first-result` | Off | Explicitly select current default first-result behavior. |
| `--result-limit N` | `10` | Positive maximum number of candidates to list or select. |

Search, selection, and first-result flags are mutually exclusive. There is no mdl `--config`, `--no-db`, source-selection, or command-line quality flag. Disable history or change quality in TOML instead. Upstream `rip` flags are not mdl flags, and this package does not install a `rip` command.

## Dispatch precedence

Avoid combining action flags. If combined, the implementation selects the first matching action:

1. Help exits during argument parsing.
2. `--setup`
3. `--set-arl`
4. `--sync-db`
5. `--gui`
6. Positional input
7. Bare invocation

An optional flag value consumes the next argument. For example, `mdl --sync-db PATH` treats PATH as the library directory, not a search query.

## Examples

```bash
mdl "Artist - Track"
mdl -v "Artist - Track"
mdl "https://open.spotify.com/track/TRACK_ID"
mdl "https://open.spotify.com/playlist/PLAYLIST_ID?si=SHARE_ID"
mdl "https://open.spotify.com/album/ALBUM_ID"
mdl "spotify:track:TRACK_ID"
mdl "spotify:playlist:PLAYLIST_ID"
mdl "spotify:album:ALBUM_ID"
mdl --setup
mdl --set-arl
mdl --sync-db
mdl --sync-db "/path/to/library"
mdl --gui
mdl-gui
```

Uppercase IDs are placeholders. Spotify share-query parameters are ignored when extracting the item ID.

## Download behavior

Search returns the first Deezer result. Spotify input resolves artist/title metadata, then performs the same Deezer matching for each track. The supplied Spotify ID does not establish an exact Deezer match.

Downloads use `downloads.folder` and `deezer.quality` from the mdl session config. A valid ARL is required. Tracks are processed sequentially; batch processing pauses between initial tracks.

With download history enabled, a single-track request can prompt to skip or redownload a duplicate. Batch requests initially skip duplicates, then offer selection for redownload in an interactive terminal. Noninteractive execution skips the review. Use `--select` for match selection, `s` to skip, or `q` to cancel. EOF skips selection. Search-only queries can retry without the artist/title separator if no matches are found.

Track and album links use Spotify app credentials. Playlist retrieval first uses app credentials, then retries with user authentication on HTTP 401/403/404. This includes failures during pagination. User authentication can open a browser and requires access to private playlists.

## Database sync

Sync recursively scans files with lowercase `.mp3`, `.flac`, `.m4a`, or `.ogg` suffixes. Files need title and artist tags. It searches by ISRC when present, otherwise artist/title, and records the first matching Deezer ID.

An unsuccessful ISRC search does not perform a second artist/title search. Files without usable tags or matches are skipped. Enable verbose output for per-file diagnostics.

Sync needs Deezer login and `database.downloads_enabled = true` to retain results. It reads audio tags without modifying files. Repeated runs do not duplicate already recorded IDs.

## Errors and cancellation

Ctrl+C cancels CLI download processing. Help exits successfully; argparse errors and missing required config can exit nonzero. Several network/auth/download failures are caught and printed without setting a nonzero process status. Automation must inspect the summary and output files, not only the exit code.

GUI cancellation has different thread behavior and is not a guarantee of interruption during every blocking external request.

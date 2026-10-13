# Configuration reference

Applies to music-downloader `0.1.0` with bundled streamrip revision `095ec9fe0c1662b32b42e202d86dbc0159a94abf`.

Setup writes the full inherited schema plus Spotify settings. This reference covers every key. **Inherited/inactive** means mdl stores the key but its current download path does not use it. This is not a promise that upstream behavior is available through mdl.

Values use TOML types: quoted strings, unquoted integers, `true`/`false`, and arrays such as `[]`. Do not paste a fragment over the whole file. Setup is the supported way to create a complete config.

## Files and precedence

CLI lookup order:

1. Platform config directory: macOS `~/Library/Application Support/music-downloader`, Linux `${XDG_CONFIG_HOME:-~/.config}/music-downloader`, Windows `%APPDATA%/music-downloader`.
2. `~/mdl-config.toml`.
3. `./mdl-config.toml`.

Each location contains `mdl-config.toml`. An unreadable/invalid candidate is skipped after a warning. The development GUI uses the same legacy-aware path lookup for editing and downloads.

Standalone streamrip config paths are macOS `~/Library/Application Support/streamrip/config.toml`, Linux `~/.config/streamrip/config.toml`, and Windows `~/AppData/Roaming/streamrip/config.toml`.

Mdl values override the in-memory streamrip session. A config matching streamrip defaults can also receive persisted overrides. Independently customized streamrip configs, including custom paths, remain unchanged during setup/download overrides. ARL refresh intentionally updates the credential in both files.

Unknown mdl keys have no runtime mapping. Types and ranges are not comprehensively validated at startup. Invalid values can fail later in the download path.

## `[downloads]`

| Key | Type / setup default | Effect in mdl |
| --- | --- | --- |
| `folder` | String; `~/Music/Music Downloader` expanded at setup | Audio destination. Mdl expands `~` before use. Set a nonempty writable path. |
| `source_subdirectories` | Boolean; `false` | Inherited/inactive: upstream per-source folders. Mdl downloads directly to `folder`. |
| `disc_subdirectories` | Boolean; `true` | For a matched multidisc album, place audio under `Disc N`. |
| `concurrency` | Boolean; `true` | Controls the engine download semaphore; mdl still processes batch tracks sequentially. Does not enable parallel playlist downloads. |
| `max_connections` | Integer; `6` | Engine concurrent-download limit. With concurrency enabled, nonpositive values are unlimited; upstream recommends `-1`. With concurrency disabled, the limit is one. |
| `requests_per_minute` | Integer; `60` | Inherited/inactive for Deezer API calls. Mdl's batch delay is separate and not configurable here. |
| `verify_ssl` | Boolean; `true` | Certificate verification for the aiohttp audio/artwork session. Keep enabled. Does not configure the separate Deezer API or Spotify client. |

The engine semaphore is shared within a process; changing connection limits during active work is not a supported tuning workflow.

## `[deezer]`

| Key | Type / setup default | Effect in mdl |
| --- | --- | --- |
| `arl` | String; supplied during setup | Required Deezer authentication cookie. Treat as a secret. Use `mdl --set-arl` for validated refresh. |
| `quality` | Integer; `1` | `1`: 320kbps MP3. `2`: FLAC, subject to account access and availability. Other integer values are mapped to `1`; directly requesting 128kbps with `0` is not supported. |
| `lower_quality_if_not_available` | Boolean; `true` | Walk to lower available quality when the requested file size is unavailable. Can fall back from FLAC to 320kbps/128kbps. License denial does not guarantee this fallback. |
| `use_deezloader` | Boolean; `true` | Inherited/inactive. Does not bypass mdl's ARL requirement or control its encrypted URL fallback. |
| `deezloader_warnings` | Boolean; `true` | Inherited/inactive warnings for upstream's deezloader path. |

## `[spotify]`

| Key | Type / setup default | Effect in mdl |
| --- | --- | --- |
| `client_id` | String; omitted/commented when not supplied | Spotify app ID. Empty/missing uses a bundled fallback ID. Supply your own ID and secret together. |
| `client_secret` | String; omitted/commented when not supplied | Spotify app secret. Empty/missing uses a bundled fallback secret. Treat your own value as private. |

Register `http://127.0.0.1:8888/callback` for user OAuth. Playlist scopes are `playlist-read-private playlist-read-collaborative`. App/user restrictions and private-playlist permissions still apply. Tokens are cached at `~/.cache-music-downloader-spotify`. No configurable backend URL or hosted resolver exists in this release.

## `[database]`

| Key | Type / setup default | Effect in mdl |
| --- | --- | --- |
| `downloads_enabled` | Boolean; `true` | Persist downloaded Deezer IDs and check duplicates. False disables both retention and duplicate detection. |
| `downloads_path` | String; platform streamrip data directory plus `downloads.db` | Download-history SQLite file. Empty paths are filled by repair; `~` expands without relocating a populated path. |
| `failed_downloads_enabled` | Boolean; `true` | Provide the engine's failed-item database. Does not mean every mdl error is recorded. |
| `failed_downloads_path` | String; same data directory plus `failed_downloads.db` | Failed-item SQLite file. Same path repair rules. Mdl has no failed-download repair command. |

Setup's streamrip data directory is macOS `~/Library/Application Support/streamrip`, Linux `${XDG_DATA_HOME:-~/.local/share}/streamrip`, or Windows `%APPDATA%/streamrip`. These data paths are separate from the standalone streamrip config path.

`mdl --sync-db` uses these flags and paths. There is no `--no-db` flag; change `downloads_enabled` in TOML.

## `[artwork]`

| Key | Type / default | Effect in mdl |
| --- | --- | --- |
| `embed` | Boolean; `true` | Embed cover artwork in the downloaded audio file. |
| `embed_size` | String; `"large"` | Requested embedded cover size: `thumbnail`, `small`, `large`, or `original`. Original images can exceed tagging/container limits. |
| `embed_max_width` | Integer; `-1` | Positive value limits the embedded image's longest dimension in pixels; otherwise no additional resize. |
| `save_artwork` | Boolean; `true` | Save the largest available cover in the shared destination artwork directory. |
| `saved_max_width` | Integer; `-1` | Positive value limits the saved cover's longest dimension; otherwise no additional resize. |

Mdl uses `.artwork/cover.jpg` and `.artwork/__artwork` under the destination. A later track can overwrite the shared saved cover. These are not per-album exported cover folders.

## `[filepaths]`

| Key | Type / default | Effect in mdl |
| --- | --- | --- |
| `add_singles_to_folder` | Boolean; `false` | Inherited/inactive: upstream single-track album folders. |
| `folder_format` | String; `"{albumartist} - {title} ({year}) [{container}] [{bit_depth}B-{sampling_rate}kHz]"` | Inherited/inactive: upstream album folder template. Mdl uses `downloads.folder` plus optional disc folders. |
| `track_format` | String; `"{tracknumber:02}. {artist} - {title}{explicit}"` | Audio basename template. The engine appends the actual file extension. |
| `restrict_characters` | Boolean; `false` | Restrict filename characters to printable ASCII during sanitization. |
| `truncate_to` | Integer; `120` | Positive value truncates the formatted basename by characters before appending extension. Nonpositive disables this extra truncation, not the sanitizer's 255-byte cap. |

Active track placeholders: `id`, `tracknumber`, `artist`, `albumartist`, `composer`, `title`, `albumcomposer`, `explicit`. `tracknumber` is the matched Deezer album position. Missing composer fields become `Unknown`. `explicit` expands to an explicit-content suffix. Include `{id}` if otherwise identical filenames can collide.

Inherited folder placeholders include `albumartist`, `title`, `year`, `container`, `bit_depth`, `sampling_rate`, `id`, and `albumcomposer`. They are not used for mdl's destination path.

## `[conversion]`

| Key | Type / default | Effect in mdl |
| --- | --- | --- |
| `enabled` | Boolean; `false` | Convert after tagging. Requires FFmpeg. Successful conversion removes the original source file. |
| `codec` | String; `"ALAC"` | Engine codecs: `FLAC`, `ALAC`, `MP3`, `OPUS`, `OGG`/`VORBIS`, `AAC`/`M4A`. The setup menu offers ALAC, MP3, FLAC, and OGG. |
| `sampling_rate` | Integer; `48000` | Sampling-rate ceiling in Hz for lossless conversion. Ignored by the engine's lossy conversion path. |
| `bit_depth` | Integer; `24` | Lossless sample-format limit; documented choices are 16 or 24. Ignored for lossy conversion. |
| `lossy_bitrate` | Integer; `320` | Inherited but not passed by the track converter. Changing it does not set actual lossy output bitrate. |

Current converter defaults: MP3 V0, Vorbis quality 6, Opus 128kbps, AAC 256kbps. AAC needs FFmpeg's `libfdk_aac` encoder. Disabling conversion preserves the downloaded source format/quality.

## `[metadata]`

All keys are inherited/inactive in mdl's `PendingTrack` path. Tags use the matched Deezer album; Spotify playlist positions/names are not applied.

| Key | Type / default | Upstream purpose |
| --- | --- | --- |
| `set_playlist_to_album` | Boolean; `true` | Replace album tag with playlist name in upstream playlist processing. |
| `renumber_playlist_tracks` | Boolean; `true` | Replace track number with playlist position in upstream playlist processing. |
| `exclude` | Array of strings; `[]` | Metadata tags excluded by upstream callers that pass this argument. Mdl does not pass it to tagging. |

## `[cli]`

| Key | Type / default | Effect in mdl |
| --- | --- | --- |
| `text_output` | Boolean; `true` | Inherited/inactive. Does not silence mdl's printed status/summary messages. |
| `progress_bars` | Boolean; `true` | Enable engine audio-download progress callbacks. Does not disable ordinary status output. |
| `max_search_results` | Integer; `100` | Inherited/inactive interactive upstream search-menu limit. Mdl downloads the first match and has no such menu. |

## `[qobuz]`

Entire section is inherited/inactive. Mdl does not instantiate a Qobuz client or fall back to Qobuz.

| Key | Type / default | Upstream purpose |
| --- | --- | --- |
| `quality` | Integer; `3` | Upstream quality levels: 1 MP3, 2 CD-quality, 3/4 higher-resolution FLAC tiers. |
| `download_booklets` | Boolean; `true` | Download album PDF booklets. |
| `use_auth_token` | Boolean; `false` | Select token authentication instead of email/password-hash authentication. |
| `email_or_userid` | String; `""` | Email, or user ID with token authentication. |
| `password_or_token` | String; `""` | Password hash or token; not a plaintext-password field. Secret. |
| `app_id` | String; `""` | Engine app identifier; leave engine-managed values intact. |
| `secrets` | Array of strings; `[]` | Engine app secrets; leave engine-managed values intact. |

## `[tidal]`

Entire section is inherited/inactive. Mdl does not provide Tidal download or OAuth entrypoints.

| Key | Type / default | Upstream purpose |
| --- | --- | --- |
| `quality` | Integer; `3` | Historical engine quality tier: 0/1 AAC, 2 FLAC, 3 MQA. Not a current-service guarantee. |
| `download_videos` | Boolean; `true` | Upstream video downloads. |
| `user_id` | String; `""` | Engine-managed user identifier. |
| `country_code` | String; `""` | Engine-managed account region. |
| `access_token` | String; `""` | Engine-managed access token. Secret. |
| `refresh_token` | String; `""` | Engine-managed refresh token. Secret. |
| `token_expiry` | String; `""` | Engine-managed token expiry marker. |

## `[soundcloud]`

Entire section is inherited/inactive. No SoundCloud input path is exposed by mdl.

| Key | Type / default | Upstream purpose |
| --- | --- | --- |
| `quality` | Integer; `0` | Upstream stream quality. |
| `client_id` | String; `""` | Upstream app identifier. |
| `app_version` | String; `""` | Upstream app version identifier. |

## `[youtube]`

Entire section is inherited/inactive. No YouTube input path is exposed by mdl.

| Key | Type / default | Upstream purpose |
| --- | --- | --- |
| `quality` | Integer; `0` | Upstream audio-quality selector. |
| `download_videos` | Boolean; `false` | Download video alongside audio. |
| `video_downloads_folder` | String; `""` in mdl's generated schema | Upstream video destination; standalone user defaults can supply a nonempty path. |

## `[qobuz_filters]`

Entire section is inherited/inactive. Mdl does not request artist discographies.

| Key | Type / default | Upstream purpose |
| --- | --- | --- |
| `extras` | Boolean; `false` | Filter special editions, live material, and extras. |
| `repeats` | Boolean; `false` | Choose one version of repeated album titles. |
| `non_albums` | Boolean; `false` | Filter EPs and singles. |
| `features` | Boolean; `false` | Filter albums attributed to other artists. |
| `non_studio_albums` | Boolean; `false` | Filter non-studio albums. |
| `non_remaster` | Boolean; `false` | Filter non-remastered albums. |

## `[lastfm]`

Entire section is inherited/inactive. Mdl has no Last.fm input path.

| Key | Type / setup default | Upstream purpose |
| --- | --- | --- |
| `source` | String; `"deezer"` | Source used for upstream Last.fm title matching. Mdl overrides the template's `qobuz` default during setup. |
| `fallback_source` | String; `""` | Alternate upstream Last.fm search source. Does not enable general download fallback. |

## `[misc]`

| Key | Type / default | Effect in mdl |
| --- | --- | --- |
| `version` | String; `"2.2.0"` | Streamrip schema version, not the mdl release version. Leave it intact; mdl's parser upgrades old markers in memory. |
| `check_for_updates` | Boolean; `true` | Inherited/inactive upstream update notification. No mdl update checker. |

## Setup, repair, and safety

Setup defaults above differ from missing-key repair: repair draws from the inherited template, where Deezer quality is 2 and download folder is blank. Repair fills missing schema keys but does not validate all existing values or authenticate credentials.

Setup validates ARL but offers an explicit continue-anyway choice after failure. ARL refresh is stricter: failed validation never persists the proposed credential. Setup advanced prompts preserve current values; blank skip behavior depends on the prompt. Unknown keys/comments survive CLI setup and migration.

CLI credential/config writers use private same-directory temp files and atomic replacement. Each file is atomic, not the pair: recovery is attempted after a second-write failure, but a crash can leave different ARLs. POSIX files use mode 600; Windows access control is managed by the OS, not POSIX modes.

The development GUI masks secret fields, parses arrays as TOML, and saves only edited fields against the latest disk document using the secure writer. Unknown keys, comments, and unrelated external edits remain intact. It is not a complete schema validator. Published `0.1.0` retains the older editor limitations.

All source descriptions come from the pinned schema, mdl mapping/dispatch, and the actual engine consumers. Upstream template comments can describe paths or flags that mdl does not expose.

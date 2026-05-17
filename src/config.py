import sys
import os
import tempfile
import logging
from pathlib import Path
import tomlkit

_log = logging.getLogger("mdl")


def _secure_write(path: Path, content: str) -> None:
    """Atomically write *content* to *path*, then chmod 600 on POSIX."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
    if os.name == "posix":
        try:
            os.chmod(path, 0o600)
        except Exception as err:
            _log.warning("mdl: could not chmod 600 %s: %s", path, err)

# --- Monkey-patch streamrip to handle outdated configs and missing fields ---
import streamrip.config
from streamrip.config import Config

# 1. Bypass OutdatedConfigError and auto-upgrade version
_original_from_toml = streamrip.config.ConfigData.from_toml


@classmethod
def _patched_from_toml(cls, toml_str: str):
    from tomlkit.api import parse, dumps

    toml = parse(toml_str)
    try:
        v = toml["misc"]["version"]
        if v != streamrip.config.CURRENT_CONFIG_VERSION:
            logging.getLogger("streamrip").info(
                f"Auto-upgrading config version from {v} to {streamrip.config.CURRENT_CONFIG_VERSION}"
            )
            toml["misc"]["version"] = streamrip.config.CURRENT_CONFIG_VERSION
            # Ensure missing Deezer fields are present in the TOML before parsing
            if "deezer" in toml:
                if "lower_quality_if_not_available" not in toml["deezer"]:
                    toml["deezer"]["lower_quality_if_not_available"] = True
                if "use_deezloader" not in toml["deezer"]:
                    toml["deezer"]["use_deezloader"] = True
                if "deezloader_warnings" not in toml["deezer"]:
                    toml["deezer"]["deezloader_warnings"] = True

            # Re-serialize so the original from_toml can parse it
            toml_str = dumps(toml)
    except Exception:
        pass
    return _original_from_toml(toml_str)


streamrip.config.ConfigData.from_toml = _patched_from_toml


def _apply_progress_color_scheme() -> None:
    """Align streamrip progress display with music-downloader's CLI color scheme."""
    try:
        from rich.console import Group
        from rich.live import Live
        from rich.progress import (
            BarColumn,
            Progress,
            TextColumn,
            TimeRemainingColumn,
            TransferSpeedColumn,
        )
        from rich.text import Text
        import streamrip.progress as sr_progress

        class _ThemedProgressManager:
            def __init__(self):
                self.started = False
                self.progress = Progress(
                    TextColumn("[bold cyan]{task.description}"),
                    BarColumn(
                        bar_width=None,
                        style="cyan",
                        complete_style="green",
                        finished_style="green",
                        pulse_style="cyan",
                    ),
                    TextColumn("[bold cyan]{task.percentage:>3.1f}%"),
                    "[cyan]•[/cyan]",
                    TransferSpeedColumn(),
                    "[cyan]•[/cyan]",
                    TimeRemainingColumn(),
                    console=sr_progress.console,
                )
                self.task_titles = []
                self.prefix = Text.assemble(
                    ("Downloading ", "bold cyan"), overflow="ellipsis"
                )
                self._text_cache = self.gen_title_text()
                self.live = Live(
                    Group(self._text_cache, self.progress),
                    refresh_per_second=10,
                )

            def get_callback(self, total: int, desc: str):
                if not self.started:
                    self.live.start()
                    self.started = True

                task = self.progress.add_task(desc, total=total)

                def _callback_update(x: int):
                    self.progress.update(task, advance=x)
                    self.live.update(Group(self.get_title_text(), self.progress))

                def _callback_done():
                    self.progress.update(task, visible=False)

                return sr_progress.Handle(_callback_update, _callback_done)

            def cleanup(self):
                if self.started:
                    self.live.stop()

            def add_title(self, title: str):
                self.task_titles.append(title.strip())
                self._text_cache = self.gen_title_text()

            def remove_title(self, title: str):
                self.task_titles.remove(title.strip())
                self._text_cache = self.gen_title_text()

            def gen_title_text(self):
                from rich.rule import Rule

                titles = ", ".join(self.task_titles[:3])
                if len(self.task_titles) > 3:
                    titles += "..."
                title_text = self.prefix + Text(titles, style="cyan")
                return Rule(title_text, style="cyan")

            def get_title_text(self):
                return self._text_cache

        sr_progress._p.cleanup()
        sr_progress.ProgressManager = _ThemedProgressManager
        sr_progress._p = _ThemedProgressManager()
    except Exception:
        # Styling should never block core functionality.
        pass


_apply_progress_color_scheme()
# --------------------------------------------------------------------------


def load_config_with_path(verbose: bool = False) -> tuple[dict, str | None]:
    """Load configuration from mdl-config.toml file, returning (data, path).

    Searches in (order of preference):
    1. Platform-specific app-support config path (Updated)
    2. User home directory (Legacy)
    3. Current working directory (Legacy)
    """
    modern_path = _get_mdl_config_path()
    legacy_paths = [
        Path.home() / "mdl-config.toml",
        Path("mdl-config.toml"),
    ]

    # If updated config exists, use it
    if modern_path.exists():
        try:
            with open(modern_path, "r", encoding="utf-8") as f:
                modern_config = tomlkit.parse(f.read())
        except Exception as e:
            print(f"Warning: Could not parse updated config at {modern_path}: {e}")
        else:
            return modern_config, str(modern_path)

    # Fallback to legacy paths
    for config_path in legacy_paths:
        if config_path.exists():
            if verbose:
                print(f"Note: Using legacy config found at {config_path}.")
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return tomlkit.parse(f.read()), str(config_path)
            except Exception as e:
                print(f"Warning: Could not parse config at {config_path}: {e}")
                continue

    return {}, None


def load_config(verbose: bool = False) -> dict:
    """Load configuration from mdl-config.toml file."""
    data, _ = load_config_with_path(verbose=verbose)
    return data


def is_streamrip_config_customized() -> bool:
    """Check if the user's streamrip config differs from the default template."""
    config_path = Path(get_default_config_path())
    if not config_path.exists():
        return False

    # Generate a default config in a temporary location
    try:
        from streamrip.config import set_user_defaults

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "config.toml"
            set_user_defaults(str(tmp_path))

            with open(tmp_path, "r", encoding="utf-8") as f:
                default_toml = tomlkit.parse(f.read())

            with open(config_path, "r", encoding="utf-8") as f:
                user_toml = tomlkit.parse(f.read())

            # Remove volatile/absolute path keys before comparison
            for toml_obj in [default_toml, user_toml]:
                if "downloads" in toml_obj and "folder" in toml_obj["downloads"]:
                    del toml_obj["downloads"]["folder"]
                if "database" in toml_obj:
                    if "downloads_path" in toml_obj["database"]:
                        del toml_obj["database"]["downloads_path"]
                    if "failed_downloads_path" in toml_obj["database"]:
                        del toml_obj["database"]["failed_downloads_path"]
                if "misc" in toml_obj and "version" in toml_obj["misc"]:
                    del toml_obj["misc"]["version"]

            return default_toml != user_toml
    except Exception as e:
        print(f"Warning: Could not perform config comparison: {e}")
        return True  # Default to safe mode on error

    return False


def ensure_streamrip_config_exists() -> str:
    """Ensure the streamrip config file exists and return its path."""
    config_path = get_default_config_path()

    if not Path(config_path).exists():
        print(
            f"Streamrip config not found at {config_path}, creating default config..."
        )
        try:
            Path(config_path).parent.mkdir(parents=True, exist_ok=True)
            from streamrip.config import set_user_defaults

            set_user_defaults(config_path)
            print(f"Created default streamrip config at {config_path}")
        except Exception as e:
            print(f"Warning: Could not create default streamrip config: {e}")
            try:
                Path(config_path).touch()
            except Exception:
                pass

    return config_path


def get_default_config_path() -> str:
    """Get the default streamrip config path for the current platform."""
    if sys.platform == "darwin":  # macOS
        return str(Path.home() / "Library/Application Support/streamrip/config.toml")
    elif sys.platform == "win32":  # Windows
        return str(Path.home() / "AppData/Roaming/streamrip/config.toml")
    else:  # Linux and others
        return str(Path.home() / ".config/streamrip/config.toml")


def merge_mdl_config_into_streamrip(
    streamrip_config_path: str, mdl_config_data: dict
) -> None:
    """Merge mdl-config.toml values into streamrip's config.toml on disk."""
    if not mdl_config_data:
        return

    MERGE_SECTIONS = {
        "downloads",
        "qobuz",
        "tidal",
        "deezer",
        "soundcloud",
        "youtube",
        "artwork",
        "metadata",
        "filepaths",
        "database",
        "lastfm",
        "cli",
        "misc",
        "conversion",
        "qobuz_filters",
    }

    with open(streamrip_config_path, "r", encoding="utf-8") as f:
        sr_config = tomlkit.parse(f.read())

    for mdl_section, mdl_values in mdl_config_data.items():
        if mdl_section in MERGE_SECTIONS:
            sr_section = mdl_section
        else:
            continue

        if sr_section not in sr_config or not isinstance(mdl_values, dict):
            continue

        for key, value in mdl_values.items():
            if key in sr_config[sr_section]:
                if sr_section == "misc" and key == "version":
                    continue
                if mdl_section == "downloads" and key == "folder":
                    value = os.path.expanduser(value)
                sr_config[sr_section][key] = value

    with open(streamrip_config_path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(sr_config))


def apply_config_overrides(config: Config, config_data: dict) -> None:
    """Apply configuration overrides from mdl-config.toml to the streamrip config."""
    is_custom = is_streamrip_config_customized()
    if is_custom:
        logging.getLogger("music-downloader").info(
            "Streamrip config has manual modifications. Using in-memory overrides from mdl-config.toml for this session."
        )

    # Apply all values to config.session
    _apply_to_session(config.session, config_data)
    config.session.update_toml()

    # If NOT customized, we sync back to config.file and write to disk
    if not is_custom:
        _apply_to_session(config.file, config_data)
        config.file.update_toml()
        config.save_file()


def _apply_to_session(session, config_data: dict) -> None:
    """Internal helper to map mdl-config data to a streamrip ConfigData session."""
    if "deezer" in config_data:
        deezer = config_data["deezer"]
        if deezer.get("arl") is not None:
            session.deezer.arl = deezer["arl"]
        if deezer.get("quality") is not None:
            mdl_quality = int(deezer["quality"])
            # MDL quality choices:
            # 1 = 320kbps MP3
            # 2 = FLAC
            #
            # Streamrip/Deezer uses its own internal quality enum.
            # Map MDL values explicitly instead of passing them through directly.
            if mdl_quality == 1:
                session.deezer.quality = 0
            elif mdl_quality == 2:
                session.deezer.quality = 2
            else:
                session.deezer.quality = 0

        if deezer.get("use_deezloader") is not None:
            session.deezer.use_deezloader = deezer["use_deezloader"]
        if deezer.get("deezloader_warnings") is not None:
            session.deezer.deezloader_warnings = deezer["deezloader_warnings"]

    if "qobuz" in config_data:
        qobuz = config_data["qobuz"]
        if qobuz.get("email_or_userid") is not None:
            session.qobuz.email_or_userid = qobuz["email_or_userid"]
        if qobuz.get("password_or_token") is not None:
            session.qobuz.password_or_token = qobuz["password_or_token"]
        if qobuz.get("use_auth_token") is not None:
            session.qobuz.use_auth_token = qobuz["use_auth_token"]
        if qobuz.get("app_id") is not None:
            session.qobuz.app_id = qobuz["app_id"]
        if qobuz.get("quality") is not None:
            session.qobuz.quality = qobuz["quality"]
        if qobuz.get("download_booklets") is not None:
            session.qobuz.download_booklets = qobuz["download_booklets"]
        if qobuz.get("secrets") is not None:
            session.qobuz.secrets = qobuz["secrets"]

    if "tidal" in config_data:
        tidal = config_data["tidal"]
        if tidal.get("user_id") is not None:
            session.tidal.user_id = tidal["user_id"]
        if tidal.get("country_code") is not None:
            session.tidal.country_code = tidal["country_code"]
        if tidal.get("access_token") is not None:
            session.tidal.access_token = tidal["access_token"]
        if tidal.get("refresh_token") is not None:
            session.tidal.refresh_token = tidal["refresh_token"]
        if tidal.get("token_expiry") is not None:
            session.tidal.token_expiry = tidal["token_expiry"]
        if tidal.get("quality") is not None:
            session.tidal.quality = tidal["quality"]
        if tidal.get("download_videos") is not None:
            session.tidal.download_videos = tidal["download_videos"]

    if "soundcloud" in config_data:
        soundcloud = config_data["soundcloud"]
        if soundcloud.get("client_id") is not None:
            session.soundcloud.client_id = soundcloud["client_id"]
        if soundcloud.get("app_version") is not None:
            session.soundcloud.app_version = soundcloud["app_version"]
        if soundcloud.get("quality") is not None:
            session.soundcloud.quality = soundcloud["quality"]

    if "youtube" in config_data:
        youtube = config_data["youtube"]
        if youtube.get("video_downloads_folder") is not None:
            session.youtube.video_downloads_folder = youtube["video_downloads_folder"]
        if youtube.get("quality") is not None:
            session.youtube.quality = youtube["quality"]
        if youtube.get("download_videos") is not None:
            session.youtube.download_videos = youtube["download_videos"]

    if "downloads" in config_data:
        downloads = config_data["downloads"]
        if downloads.get("folder") is not None:
            session.downloads.folder = os.path.expanduser(downloads["folder"])
        if downloads.get("source_subdirectories") is not None:
            session.downloads.source_subdirectories = downloads["source_subdirectories"]
        if downloads.get("disc_subdirectories") is not None:
            session.downloads.disc_subdirectories = downloads["disc_subdirectories"]
        if downloads.get("concurrency") is not None:
            session.downloads.concurrency = downloads["concurrency"]
        if downloads.get("max_connections") is not None:
            session.downloads.max_connections = downloads["max_connections"]
        if downloads.get("requests_per_minute") is not None:
            session.downloads.requests_per_minute = downloads["requests_per_minute"]
        if downloads.get("verify_ssl") is not None:
            session.downloads.verify_ssl = downloads["verify_ssl"]

    if "artwork" in config_data:
        artwork = config_data["artwork"]
        if artwork.get("embed") is not None:
            session.artwork.embed = artwork["embed"]
        if artwork.get("embed_size") is not None:
            session.artwork.embed_size = artwork["embed_size"]
        if artwork.get("embed_max_width") is not None:
            session.artwork.embed_max_width = artwork["embed_max_width"]
        if artwork.get("save_artwork") is not None:
            session.artwork.save_artwork = artwork["save_artwork"]
        if artwork.get("saved_max_width") is not None:
            session.artwork.saved_max_width = artwork["saved_max_width"]

    if "metadata" in config_data:
        metadata = config_data["metadata"]
        if metadata.get("set_playlist_to_album") is not None:
            session.metadata.set_playlist_to_album = metadata["set_playlist_to_album"]
        if metadata.get("renumber_playlist_tracks") is not None:
            session.metadata.renumber_playlist_tracks = metadata[
                "renumber_playlist_tracks"
            ]
        if metadata.get("exclude") is not None:
            session.metadata.exclude = metadata["exclude"]

    if "filepaths" in config_data:
        filepaths = config_data["filepaths"]
        if filepaths.get("add_singles_to_folder") is not None:
            session.filepaths.add_singles_to_folder = filepaths["add_singles_to_folder"]
        if filepaths.get("folder_format") is not None:
            session.filepaths.folder_format = filepaths["folder_format"]
        if filepaths.get("track_format") is not None:
            session.filepaths.track_format = filepaths["track_format"]
        if filepaths.get("restrict_characters") is not None:
            session.filepaths.restrict_characters = filepaths["restrict_characters"]
        if filepaths.get("truncate_to") is not None:
            session.filepaths.truncate_to = filepaths["truncate_to"]

    if "conversion" in config_data:
        conversion = config_data["conversion"]
        if conversion.get("enabled") is not None:
            session.conversion.enabled = conversion["enabled"]
        if conversion.get("codec") is not None:
            session.conversion.codec = conversion["codec"]
        if conversion.get("sampling_rate") is not None:
            session.conversion.sampling_rate = conversion["sampling_rate"]
        if conversion.get("bit_depth") is not None:
            session.conversion.bit_depth = conversion["bit_depth"]
        if conversion.get("lossy_bitrate") is not None:
            session.conversion.lossy_bitrate = conversion["lossy_bitrate"]

    if "qobuz_filters" in config_data:
        qobuz_filters = config_data["qobuz_filters"]
        if qobuz_filters.get("extras") is not None:
            session.qobuz_filters.extras = qobuz_filters["extras"]
        if qobuz_filters.get("repeats") is not None:
            session.qobuz_filters.repeats = qobuz_filters["repeats"]
        if qobuz_filters.get("non_albums") is not None:
            session.qobuz_filters.non_albums = qobuz_filters["non_albums"]
        if qobuz_filters.get("features") is not None:
            session.qobuz_filters.features = qobuz_filters["features"]
        if qobuz_filters.get("non_studio_albums") is not None:
            session.qobuz_filters.non_studio_albums = qobuz_filters["non_studio_albums"]
        if qobuz_filters.get("non_remaster") is not None:
            session.qobuz_filters.non_remaster = qobuz_filters["non_remaster"]

    if "database" in config_data:
        database = config_data["database"]
        if database.get("downloads_enabled") is not None:
            session.database.downloads_enabled = database["downloads_enabled"]
        if database.get("downloads_path") is not None:
            session.database.downloads_path = database["downloads_path"]
        if database.get("failed_downloads_enabled") is not None:
            session.database.failed_downloads_enabled = database[
                "failed_downloads_enabled"
            ]
        if database.get("failed_downloads_path") is not None:
            session.database.failed_downloads_path = database["failed_downloads_path"]

    if "lastfm" in config_data:
        lastfm = config_data["lastfm"]
        if lastfm.get("source") is not None:
            session.lastfm.source = lastfm["source"]
        if lastfm.get("fallback_source") is not None:
            session.lastfm.fallback_source = lastfm["fallback_source"]

    if "cli" in config_data:
        cli = config_data["cli"]
        if cli.get("text_output") is not None:
            session.cli.text_output = cli["text_output"]
        if cli.get("progress_bars") is not None:
            session.cli.progress_bars = cli["progress_bars"]
        if cli.get("max_search_results") is not None:
            session.cli.max_search_results = cli["max_search_results"]

    if "misc" in config_data:
        misc = config_data["misc"]
        if misc.get("version") is not None:
            session.misc.version = misc["version"]
        if misc.get("check_for_updates") is not None:
            session.misc.check_for_updates = misc["check_for_updates"]


def _get_mdl_config_dir() -> Path:
    import appdirs

    return Path(appdirs.user_config_dir("music-downloader", appauthor=False))


def _get_streamrip_data_dir() -> Path:
    import appdirs

    return Path(appdirs.user_data_dir("streamrip", appauthor=False))


def _default_database_paths() -> tuple[str, str]:
    base = _get_streamrip_data_dir()
    return (str(base / "downloads.db"), str(base / "failed_downloads.db"))


def _get_mdl_config_path() -> Path:
    return _get_mdl_config_dir() / "mdl-config.toml"


def _validate_deezer_arl(arl: str) -> bool:
    import asyncio

    try:
        from streamrip.client import DeezerClient
        from streamrip.config import Config

        sr_path = ensure_streamrip_config_exists()
        config = Config(sr_path)
        config.session.deezer.arl = arl
        client = DeezerClient(config)

        async def _try_login() -> bool:
            await client.login()
            return getattr(client, "logged_in", False)

        return asyncio.run(_try_login())
    except Exception:
        return False


def _build_config_toml(
    arl: str,
    quality: int,
    folder: str,
    spotify_id: str = "",
    spotify_secret: str = "",
    advanced: dict | None = None,
) -> str:
    import copy
    from src.schema import STREAMRIP_DEFAULTS

    doc = copy.deepcopy(STREAMRIP_DEFAULTS)

    # Required overrides
    doc["deezer"]["arl"] = arl
    doc["deezer"]["quality"] = quality
    doc["downloads"]["folder"] = os.path.expanduser(folder)

    db_path, failed_db_path = _default_database_paths()
    doc["database"]["downloads_path"] = db_path
    doc["database"]["failed_downloads_path"] = failed_db_path

    # Override lastfm source (design decision #5)
    doc["lastfm"]["source"] = "deezer"
    # Add inline comment for the override — tomlkit item-level comment
    try:
        doc["lastfm"]["source"].comment(
            'overridden from streamrip default ("qobuz") since mdl is Deezer-primary'
        )
    except Exception:
        pass

    # Apply advanced overrides
    if advanced:
        for section, keys in advanced.items():
            if isinstance(keys, dict):
                if section not in doc:
                    doc.add(section, tomlkit.table())
                for k, v in keys.items():
                    doc[section][k] = v
            else:
                doc[section] = keys

    # Append [spotify] section
    spotify_table = tomlkit.table()
    if spotify_id:
        spotify_table.add("client_id", spotify_id)
    else:
        spotify_table.add(tomlkit.comment("client_id = \"\""))
    if spotify_secret:
        spotify_table.add("client_secret", spotify_secret)
    else:
        spotify_table.add(tomlkit.comment("client_secret = \"\""))
    doc.add("spotify", spotify_table)

    content = tomlkit.dumps(doc)

    # Prepend banner (design decision #7)
    banner = (
        "# mdl — music-downloader config\n"
        "# Contains credentials (Deezer ARL, Spotify client_secret). Do not share.\n"
        "# Edit this file directly or run 'mdl --setup' to reconfigure.\n"
    )
    return banner + content


def ensure_mdl_config_complete() -> None:
    """On every startup: fill missing keys, fix empty db paths, rename legacy sections."""
    import copy
    from src.schema import STREAMRIP_DEFAULTS

    config_data, config_path_str = load_config_with_path()
    if not config_path_str:
        # No config yet — setup wizard handles that
        return

    config_path = Path(config_path_str)

    # Legacy-path nudge (non-blocking)
    modern_path = _get_mdl_config_path()
    legacy_home = Path.home() / "mdl-config.toml"
    if config_path == legacy_home:
        _log.info(
            "mdl: legacy config detected at %s — run 'mdl --setup' to migrate to %s",
            config_path,
            modern_path,
        )

    user_doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    changed: list[str] = []

    # Special case: rename [conversions] → [conversion]
    if "conversions" in user_doc and "conversion" not in user_doc:
        old_table = user_doc.item("conversions")
        user_doc.remove("conversions")
        user_doc.add("conversion", old_table)
        changed.append("[conversions]→[conversion]")
        _log.info(
            "mdl: renamed legacy [conversions] section to [conversion] in %s",
            config_path,
        )

    db_path, failed_db_path = _default_database_paths()
    must_fill = {
        ("database", "downloads_path"): db_path,
        ("database", "failed_downloads_path"): failed_db_path,
    }

    for section, default_values in copy.deepcopy(STREAMRIP_DEFAULTS).items():
        if not isinstance(default_values, dict):
            continue
        if section not in user_doc:
            user_doc.add(section, default_values)
            changed.append(section)
            if section == "lastfm":
                user_doc["lastfm"]["source"] = "deezer"
            # Fill must-fill keys that came in as empty defaults
            for k, fill_val in must_fill.items():
                if k[0] == section and not user_doc[section].get(k[1]):
                    user_doc[section][k[1]] = fill_val
                    parent = Path(fill_val).parent
                    try:
                        parent.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        pass
        else:
            for key, default_val in default_values.items():
                k = (section, key)
                if key not in user_doc[section]:
                    user_doc[section].add(key, default_val)
                    changed.append(f"{section}.{key}")
                    if k in must_fill and not default_val:
                        user_doc[section][key] = must_fill[k]
                        parent = Path(must_fill[k]).parent
                        try:
                            parent.mkdir(parents=True, exist_ok=True)
                        except Exception:
                            pass
                elif k in must_fill and not user_doc[section][key]:
                    user_doc[section][key] = must_fill[k]
                    parent = Path(must_fill[k]).parent
                    try:
                        parent.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        pass
                    changed.append(f"{section}.{key}")

    # Ensure [spotify] section exists
    if "spotify" not in user_doc:
        spotify_table = tomlkit.table()
        spotify_table.add(tomlkit.comment("client_id = \"\""))
        spotify_table.add(tomlkit.comment("client_secret = \"\""))
        user_doc.add("spotify", spotify_table)
        changed.append("spotify")

    if changed:
        _secure_write(config_path, tomlkit.dumps(user_doc))
        _log.info("mdl: filled in missing config keys: %s", ", ".join(changed))


def _write_or_update_config(
    path: Path,
    prompted: dict,
    advanced: dict | None = None,
) -> None:
    """Write a full config if *path* is absent/empty, otherwise fill only missing keys."""
    import copy
    from src.schema import STREAMRIP_DEFAULTS

    if not path.exists() or path.stat().st_size == 0:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = _build_config_toml(
            arl=prompted.get("arl", ""),
            quality=prompted.get("quality", 1),
            folder=prompted.get("folder", "~/Music/Music Downloader"),
            spotify_id=prompted.get("spotify_id", ""),
            spotify_secret=prompted.get("spotify_secret", ""),
            advanced=advanced,
        )
        _secure_write(path, content)
        return

    # Merge into existing file — preserve user values, fill only missing
    user_doc = tomlkit.parse(path.read_text(encoding="utf-8"))
    defaults = copy.deepcopy(STREAMRIP_DEFAULTS)

    db_path, failed_db_path = _default_database_paths()
    must_fill = {
        ("database", "downloads_path"): db_path,
        ("database", "failed_downloads_path"): failed_db_path,
    }
    changed: list[str] = []

    for section, default_values in defaults.items():
        if not isinstance(default_values, dict):
            continue
        if section not in user_doc:
            user_doc.add(section, copy.deepcopy(default_values))
            changed.append(section)
            # Apply lastfm.source override for freshly-added section
            if section == "lastfm":
                user_doc["lastfm"]["source"] = "deezer"
        else:
            for key, default_val in default_values.items():
                k = (section, key)
                if key not in user_doc[section]:
                    user_doc[section].add(key, default_val)
                    changed.append(f"{section}.{key}")
                elif k in must_fill and not user_doc[section][key]:
                    user_doc[section][key] = must_fill[k]
                    changed.append(f"{section}.{key}")

    # Apply prompted overrides (explicit user input wins)
    user_doc["deezer"]["arl"] = prompted["arl"]
    user_doc["deezer"]["quality"] = prompted["quality"]
    user_doc["downloads"]["folder"] = os.path.expanduser(prompted["folder"])

    if prompted.get("spotify_id") or prompted.get("spotify_secret"):
        if "spotify" not in user_doc:
            user_doc.add("spotify", tomlkit.table())
        user_doc["spotify"]["client_id"] = prompted.get("spotify_id", "")
        user_doc["spotify"]["client_secret"] = prompted.get("spotify_secret", "")

    # Apply advanced overrides
    if advanced:
        for section, keys in advanced.items():
            if isinstance(keys, dict):
                if section not in user_doc:
                    user_doc.add(section, tomlkit.table())
                    changed.append(section)
                for k, v in keys.items():
                    user_doc[section][k] = v
            else:
                user_doc[section] = keys

    # Ensure [spotify] section exists
    if "spotify" not in user_doc:
        spotify_table = tomlkit.table()
        spotify_table.add(tomlkit.comment("client_id = \"\""))
        spotify_table.add(tomlkit.comment("client_secret = \"\""))
        user_doc.add("spotify", spotify_table)

    _secure_write(path, tomlkit.dumps(user_doc))

    if changed:
        _log.info("mdl: filled in missing config keys: %s", ", ".join(changed))


def run_setup_wizard() -> None:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel

    console = Console()
    try:
        console.print(
            Panel.fit(
                "[bold cyan]Music Downloader Setup[/bold cyan]",
                subtitle="[dim]v1.0[/dim]",
                border_style="blue",
            )
        )

        # Check for existing config to use as defaults
        existing_config, existing_path = load_config_with_path(verbose=True)
        modern_path = _get_mdl_config_path()

        # If legacy config exists but modern doesn't, offer migration
        if (
            existing_path
            and Path(existing_path) != modern_path
            and not modern_path.exists()
        ):
            console.print(f"\n[yellow]Found legacy config at {existing_path}[/yellow]")
            if Confirm.ask(
                f"Migrate this to the modern path ({modern_path})?", default=True
            ):
                try:
                    modern_path.parent.mkdir(parents=True, exist_ok=True)
                    # We'll write the new one later, but let's note we're migrating
                    console.print(
                        "[green]✓ Values will be migrated to the new location.[/green]"
                    )
                except Exception as e:
                    console.print(f"[red]Could not create directory:[/red] {e}")

        # Set defaults based on existing config
        default_arl = existing_config.get("deezer", {}).get("arl", "")
        default_folder = existing_config.get("downloads", {}).get(
            "folder", "~/Music/Music Downloader"
        )
        default_quality = str(existing_config.get("deezer", {}).get("quality", "1"))
        default_spotify_id = existing_config.get("spotify", {}).get("client_id", "")
        default_spotify_secret = existing_config.get("spotify", {}).get(
            "client_secret", ""
        )

        # 1. Deezer ARL
        console.print("\n[bold]Step 1: Deezer ARL[/bold] [red](required)[/red]")
        console.print(
            "[dim]Your ARL is a cookie used to authenticate with Deezer. You need to create a Deezer account and login for this.[/dim]"
        )
        console.print(
            "[dim]Find it here:[/dim] [link=https://github.com/nathom/streamrip/wiki/Finding-Your-Deezer-ARL-Cookie]streamrip wiki[/link]\n"
        )
        arl = ""
        while not arl:
            arl = Prompt.ask(
                "[cyan]Paste your Deezer ARL[/cyan]", default=default_arl
            ).strip()
            if not arl:
                console.print("[red]ARL is required.[/red]")

        console.print("\n[yellow]Validating ARL...[/yellow]")
        if not _validate_deezer_arl(arl):
            console.print(
                "[bold red]Warning:[/bold red] Could not validate ARL. It might be expired or invalid."
            )
            if not Confirm.ask("Continue anyway?", default=True):
                return
        else:
            console.print("[bold green]✓ ARL is valid![/bold green]")

        # 2. Download folder
        console.print("\n[bold]Step 2: Download Folder[/bold]")
        folder = Prompt.ask(
            "[cyan]Download folder[/cyan]", default=default_folder
        ).strip()

        # 3. Quality
        console.print("\n[bold]Step 3: Audio Quality[/bold]")
        console.print(
            "  [bold white]1[/bold white] = 320kbps MP3 [dim](Standard)[/dim]"
        )
        console.print(
            "  [bold white]2[/bold white] = FLAC [dim](Lossless, requires paid Deezer)[/dim]"
        )
        quality_str = Prompt.ask(
            "[cyan]Choose quality[/cyan]", choices=["1", "2"], default=default_quality
        )
        quality = int(quality_str)

        # 4. Spotify
        console.print(
            "\n[bold]Step 4: Spotify Dev App Credentials[/bold] [dim](optional)[/dim]"
        )
        console.print(
            "[dim]MDL has built-in defaults, but you can provide your own via https://developer.spotify.com/ .[/dim]"
        )
        spotify_id = default_spotify_id
        spotify_secret = default_spotify_secret

        if Confirm.ask(
            "[cyan]Add/Update custom Spotify credentials?[/cyan]",
            default=bool(spotify_id),
        ):
            spotify_id = Prompt.ask(
                "[cyan]Spotify Client ID[/cyan]", default=spotify_id
            ).strip()
            spotify_secret = Prompt.ask(
                "[cyan]Spotify Client Secret[/cyan]",
                default=spotify_secret,
                password=True,
            ).strip()

        # 5. Advanced options
        advanced: dict | None = None
        if Confirm.ask(
            "\n[cyan]Configure advanced options now?[/cyan] "
            "[dim]You can always edit the config file later.[/dim]",
            default=False,
        ):
            from src.schema import STREAMRIP_DEFAULTS

            advanced = {}

            console.print("\n[bold]Advanced: Downloads[/bold]")
            _def_conc = str(STREAMRIP_DEFAULTS["downloads"]["concurrency"]).lower()
            conc_str = Prompt.ask(
                "[cyan]Enable concurrency (true/false)[/cyan]",
                default=_def_conc,
            ).strip().lower()
            if conc_str:
                advanced.setdefault("downloads", {})["concurrency"] = conc_str == "true"

            _def_mc = str(STREAMRIP_DEFAULTS["downloads"]["max_connections"])
            mc_str = Prompt.ask(
                "[cyan]Max connections[/cyan]", default=_def_mc
            ).strip()
            if mc_str:
                try:
                    advanced.setdefault("downloads", {})["max_connections"] = int(mc_str)
                except ValueError:
                    pass

            console.print("\n[bold]Advanced: Qobuz[/bold]")
            use_token_str = Prompt.ask(
                "[cyan]Use auth token for Qobuz? (true/false, blank=skip)[/cyan]",
                default="",
            ).strip().lower()
            if use_token_str in ("true", "false"):
                advanced.setdefault("qobuz", {})["use_auth_token"] = use_token_str == "true"
                qobuz_email = Prompt.ask(
                    "[cyan]Qobuz email or user ID (blank=skip)[/cyan]", default=""
                ).strip()
                if qobuz_email:
                    advanced.setdefault("qobuz", {})["email_or_userid"] = qobuz_email
                qobuz_pass = Prompt.ask(
                    "[cyan]Qobuz password or token (blank=skip)[/cyan]",
                    default="",
                    password=True,
                ).strip()
                if qobuz_pass:
                    advanced.setdefault("qobuz", {})["password_or_token"] = qobuz_pass

            console.print("\n[bold]Advanced: Tidal[/bold]")
            console.print(
                "[dim]Hint: full Tidal OAuth login requires `rip config --tidal` after install.[/dim]"
            )
            tidal_user_id = Prompt.ask(
                "[cyan]Tidal user ID (blank=skip)[/cyan]", default=""
            ).strip()
            if tidal_user_id:
                advanced.setdefault("tidal", {})["user_id"] = tidal_user_id
            tidal_token = Prompt.ask(
                "[cyan]Tidal access token (blank=skip)[/cyan]", default=""
            ).strip()
            if tidal_token:
                advanced.setdefault("tidal", {})["access_token"] = tidal_token

            console.print("\n[bold]Advanced: Conversion[/bold]")
            conv_enabled_str = Prompt.ask(
                "[cyan]Enable audio conversion? (true/false)[/cyan]", default="false"
            ).strip().lower()
            if conv_enabled_str in ("true", "false"):
                conv_enabled = conv_enabled_str == "true"
                advanced.setdefault("conversion", {})["enabled"] = conv_enabled
                if conv_enabled:
                    codec = Prompt.ask(
                        "[cyan]Codec[/cyan]",
                        choices=["ALAC", "MP3", "FLAC", "OGG"],
                        default="ALAC",
                    ).strip()
                    advanced.setdefault("conversion", {})["codec"] = codec

            console.print("\n[bold]Advanced: Filepaths[/bold]")
            _def_ff = STREAMRIP_DEFAULTS["filepaths"]["folder_format"]
            ff = Prompt.ask(
                "[cyan]Folder format[/cyan]", default=_def_ff
            ).strip()
            if ff and ff != _def_ff:
                advanced.setdefault("filepaths", {})["folder_format"] = ff

            if not any(advanced.values()):
                advanced = None

        prompted = {
            "arl": arl,
            "quality": quality,
            "folder": folder,
            "spotify_id": spotify_id,
            "spotify_secret": spotify_secret,
        }

        try:
            _write_or_update_config(modern_path, prompted, advanced=advanced)

            sr_path = ensure_streamrip_config_exists()
            merge_mdl_config_into_streamrip(
                sr_path,
                tomlkit.parse(modern_path.read_text(encoding="utf-8")),
            )

            console.print("\n[bold green]✓ Setup complete![/bold green]")
            console.print(f"[dim]Config saved to:[/dim] [cyan]{modern_path}[/cyan]")

            # If we migrated, suggest deleting the old one
            if existing_path and Path(existing_path) != modern_path:
                console.print(
                    f"\n[yellow]Legacy config still exists at {existing_path}[/yellow]"
                )
                if Confirm.ask("Delete the legacy config file?", default=False):
                    try:
                        os.remove(existing_path)
                        console.print("[green]✓ Legacy config deleted.[/green]")
                    except Exception as e:
                        console.print(f"[red]Error deleting file:[/red] {e}")

            console.print('\nTry: [bold white]mdl "artist - track name"[/bold white]\n')

            # Safety-net: fill any remaining gaps
            ensure_mdl_config_complete()
        except Exception as e:
            console.print(f"\n[bold red]Error saving config:[/bold red] {e}")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Setup cancelled. Exiting...[/yellow]")
        return

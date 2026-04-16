import sys
import os
import copy
import tempfile
import logging
from pathlib import Path
import tomlkit

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
            logging.getLogger("streamrip").warning(
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
# --------------------------------------------------------------------------

def load_config_with_path() -> tuple[dict, str | None]:
    """Load configuration from mdl-config.toml file, returning (data, path).

    Searches in (order of preference):
    1. Platform-specific app-support config path (Modern)
    2. User home directory (Legacy)
    3. Current working directory (Legacy)
    """
    modern_path = _get_mdl_config_path()
    legacy_paths = [
        Path.home() / "mdl-config.toml",
        Path("mdl-config.toml"),
    ]

    # If modern config exists, use it
    if modern_path.exists():
        # Check if any legacy configs are also present to warn the user
        for lp in legacy_paths:
            if lp.exists():
                print(f"Note: Using modern config at {modern_path}. Legacy config at {lp} is being ignored.")
        
        try:
            with open(modern_path, "r", encoding="utf-8") as f:
                return tomlkit.parse(f.read()), str(modern_path)
        except Exception as e:
            print(f"Warning: Could not parse modern config at {modern_path}: {e}")

    # Fallback to legacy paths
    for config_path in legacy_paths:
        if config_path.exists():
            print(f"Note: Using legacy config found at {config_path}.")
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return tomlkit.parse(f.read()), str(config_path)
            except Exception as e:
                print(f"Warning: Could not parse config at {config_path}: {e}")
                continue
    
    return {}, None


def load_config() -> dict:
    """Load configuration from mdl-config.toml file."""
    data, _ = load_config_with_path()
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
            
            with open(tmp_path, 'r', encoding='utf-8') as f:
                default_toml = tomlkit.parse(f.read())
            
            with open(config_path, 'r', encoding='utf-8') as f:
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
        return True # Default to safe mode on error

    return False


def ensure_streamrip_config_exists() -> str:
    """Ensure the streamrip config file exists and return its path."""
    config_path = get_default_config_path()

    if not Path(config_path).exists():
        print(f"Streamrip config not found at {config_path}, creating default config...")
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
        "downloads", "qobuz", "tidal", "deezer", "soundcloud", "youtube",
        "artwork", "metadata", "filepaths", "database", "lastfm", "cli", "misc",
    }
    SPECIAL_MAPPINGS = {"conversions": "conversion"}

    with open(streamrip_config_path, "r", encoding="utf-8") as f:
        sr_config = tomlkit.parse(f.read())

    for mdl_section, mdl_values in mdl_config_data.items():
        if mdl_section in MERGE_SECTIONS:
            sr_section = mdl_section
        elif mdl_section in SPECIAL_MAPPINGS:
            sr_section = SPECIAL_MAPPINGS[mdl_section]
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
        print("Streamrip config has manual modifications. Using in-memory overrides from mdl-config.toml for this session.")

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
        if deezer.get("arl") is not None: session.deezer.arl = deezer["arl"]
        if deezer.get("quality") is not None: session.deezer.quality = deezer["quality"]
        if deezer.get("use_deezloader") is not None: session.deezer.use_deezloader = deezer["use_deezloader"]
        if deezer.get("deezloader_warnings") is not None: session.deezer.deezloader_warnings = deezer["deezloader_warnings"]

    if "qobuz" in config_data:
        qobuz = config_data["qobuz"]
        if qobuz.get("email_or_userid") is not None: session.qobuz.email_or_userid = qobuz["email_or_userid"]
        if qobuz.get("password_or_token") is not None: session.qobuz.password_or_token = qobuz["password_or_token"]
        if qobuz.get("use_auth_token") is not None: session.qobuz.use_auth_token = qobuz["use_auth_token"]
        if qobuz.get("app_id") is not None: session.qobuz.app_id = qobuz["app_id"]
        if qobuz.get("quality") is not None: session.qobuz.quality = qobuz["quality"]
        if qobuz.get("download_booklets") is not None: session.qobuz.download_booklets = qobuz["download_booklets"]
        if qobuz.get("secrets") is not None: session.qobuz.secrets = qobuz["secrets"]

    if "tidal" in config_data:
        tidal = config_data["tidal"]
        if tidal.get("user_id") is not None: session.tidal.user_id = tidal["user_id"]
        if tidal.get("country_code") is not None: session.tidal.country_code = tidal["country_code"]
        if tidal.get("access_token") is not None: session.tidal.access_token = tidal["access_token"]
        if tidal.get("refresh_token") is not None: session.tidal.refresh_token = tidal["refresh_token"]
        if tidal.get("token_expiry") is not None: session.tidal.token_expiry = tidal["token_expiry"]
        if tidal.get("quality") is not None: session.tidal.quality = tidal["quality"]
        if tidal.get("download_videos") is not None: session.tidal.download_videos = tidal["download_videos"]

    if "soundcloud" in config_data:
        soundcloud = config_data["soundcloud"]
        if soundcloud.get("client_id") is not None: session.soundcloud.client_id = soundcloud["client_id"]
        if soundcloud.get("app_version") is not None: session.soundcloud.app_version = soundcloud["app_version"]
        if soundcloud.get("quality") is not None: session.soundcloud.quality = soundcloud["quality"]

    if "youtube" in config_data:
        youtube = config_data["youtube"]
        if youtube.get("video_downloads_folder") is not None: session.youtube.video_downloads_folder = youtube["video_downloads_folder"]
        if youtube.get("quality") is not None: session.youtube.quality = youtube["quality"]
        if youtube.get("download_videos") is not None: session.youtube.download_videos = youtube["download_videos"]

    if "downloads" in config_data:
        downloads = config_data["downloads"]
        if downloads.get("folder") is not None: session.downloads.folder = os.path.expanduser(downloads["folder"])
        if downloads.get("source_subdirectories") is not None: session.downloads.source_subdirectories = downloads["source_subdirectories"]
        if downloads.get("disc_subdirectories") is not None: session.downloads.disc_subdirectories = downloads["disc_subdirectories"]
        if downloads.get("concurrency") is not None: session.downloads.concurrency = downloads["concurrency"]
        if downloads.get("max_connections") is not None: session.downloads.max_connections = downloads["max_connections"]
        if downloads.get("requests_per_minute") is not None: session.downloads.requests_per_minute = downloads["requests_per_minute"]
        if downloads.get("verify_ssl") is not None: session.downloads.verify_ssl = downloads["verify_ssl"]

    if "artwork" in config_data:
        artwork = config_data["artwork"]
        if artwork.get("embed") is not None: session.artwork.embed = artwork["embed"]
        if artwork.get("embed_size") is not None: session.artwork.embed_size = artwork["embed_size"]
        if artwork.get("embed_max_width") is not None: session.artwork.embed_max_width = artwork["embed_max_width"]
        if artwork.get("save_artwork") is not None: session.artwork.save_artwork = artwork["save_artwork"]
        if artwork.get("saved_max_width") is not None: session.artwork.saved_max_width = artwork["saved_max_width"]

    if "metadata" in config_data:
        metadata = config_data["metadata"]
        if metadata.get("set_playlist_to_album") is not None: session.metadata.set_playlist_to_album = metadata["set_playlist_to_album"]
        if metadata.get("renumber_playlist_tracks") is not None: session.metadata.renumber_playlist_tracks = metadata["renumber_playlist_tracks"]
        if metadata.get("exclude") is not None: session.metadata.exclude = metadata["exclude"]

    if "filepaths" in config_data:
        filepaths = config_data["filepaths"]
        if filepaths.get("add_singles_to_folder") is not None: session.filepaths.add_singles_to_folder = filepaths["add_singles_to_folder"]
        if filepaths.get("folder_format") is not None: session.filepaths.folder_format = filepaths["folder_format"]
        if filepaths.get("track_format") is not None: session.filepaths.track_format = filepaths["track_format"]
        if filepaths.get("restrict_characters") is not None: session.filepaths.restrict_characters = filepaths["restrict_characters"]
        if filepaths.get("truncate_to") is not None: session.filepaths.truncate_to = filepaths["truncate_to"]

    if "conversions" in config_data:
        conversions = config_data["conversions"]
        if conversions.get("enabled") is not None: session.conversion.enabled = conversions["enabled"]
        if conversions.get("codec") is not None: session.conversion.codec = conversions["codec"]
        if conversions.get("sampling_rate") is not None: session.conversion.sampling_rate = conversions["sampling_rate"]
        if conversions.get("bit_depth") is not None: session.conversion.bit_depth = conversions["bit_depth"]
        if conversions.get("lossy_bitrate") is not None: session.conversion.lossy_bitrate = conversions["lossy_bitrate"]

    if "qobuz_filters" in config_data:
        qobuz_filters = config_data["qobuz_filters"]
        if qobuz_filters.get("extras") is not None: session.qobuz_filters.extras = qobuz_filters["extras"]
        if qobuz_filters.get("repeats") is not None: session.qobuz_filters.repeats = qobuz_filters["repeats"]
        if qobuz_filters.get("non_albums") is not None: session.qobuz_filters.non_albums = qobuz_filters["non_albums"]
        if qobuz_filters.get("features") is not None: session.qobuz_filters.features = qobuz_filters["features"]
        if qobuz_filters.get("non_studio_albums") is not None: session.qobuz_filters.non_studio_albums = qobuz_filters["non_studio_albums"]
        if qobuz_filters.get("non_remaster") is not None: session.qobuz_filters.non_remaster = qobuz_filters["non_remaster"]

    if "database" in config_data:
        database = config_data["database"]
        if database.get("downloads_enabled") is not None: session.database.downloads_enabled = database["downloads_enabled"]
        if database.get("downloads_path") is not None: session.database.downloads_path = database["downloads_path"]
        if database.get("failed_downloads_enabled") is not None: session.database.failed_downloads_enabled = database["failed_downloads_enabled"]
        if database.get("failed_downloads_path") is not None: session.database.failed_downloads_path = database["failed_downloads_path"]

    if "lastfm" in config_data:
        lastfm = config_data["lastfm"]
        if lastfm.get("source") is not None: session.lastfm.source = lastfm["source"]
        if lastfm.get("fallback_source") is not None: session.lastfm.fallback_source = lastfm["fallback_source"]

    if "cli" in config_data:
        cli = config_data["cli"]
        if cli.get("text_output") is not None: session.cli.text_output = cli["text_output"]
        if cli.get("progress_bars") is not None: session.cli.progress_bars = cli["progress_bars"]
        if cli.get("max_search_results") is not None: session.cli.max_search_results = cli["max_search_results"]

    if "misc" in config_data:
        misc = config_data["misc"]
        if misc.get("version") is not None: session.misc.version = misc["version"]
        if misc.get("check_for_updates") is not None: session.misc.check_for_updates = misc["check_for_updates"]


def _get_mdl_config_dir() -> Path:
    if sys.platform == "darwin": return Path.home() / "Library/Application Support/music-downloader"
    elif sys.platform == "win32": return Path.home() / "AppData/Roaming/music-downloader"
    else: return Path.home() / ".config/music-downloader"


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
    except Exception: return False


def _build_config_toml(arl: str, quality: int, folder: str, spotify_id: str = "", spotify_secret: str = "") -> str:
    lines = ["# Music Downloader Configuration", "# Edit this file or run 'mdl --setup' to reconfigure.", "", "[deezer]", f'arl = "{arl}"', f"quality = {quality}", "", "[downloads]", f'folder = "{folder}"', "", "[filepaths]", 'track_format = "{artist} - {title}{explicit}"']
    if spotify_id and spotify_secret:
        lines.extend(["", "[spotify]", f'client_id = "{spotify_id}"', f'client_secret = "{spotify_secret}"'])
    return "\n".join(lines) + "\n"


def run_setup_wizard() -> None:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel

    console = Console()
    try:
        console.print(Panel.fit(
            "[bold cyan]Music Downloader Setup[/bold cyan]",
            subtitle="[dim]v1.0[/dim]",
            border_style="blue"
        ))

        # Check for existing config to use as defaults
        existing_config, existing_path = load_config_with_path()
        modern_path = _get_mdl_config_path()
        
        # If legacy config exists but modern doesn't, offer migration
        if existing_path and Path(existing_path) != modern_path and not modern_path.exists():
            console.print(f"\n[yellow]Found legacy config at {existing_path}[/yellow]")
            if Confirm.ask(f"Migrate this to the modern path ({modern_path})?", default=True):
                try:
                    modern_path.parent.mkdir(parents=True, exist_ok=True)
                    # We'll write the new one later, but let's note we're migrating
                    console.print("[green]✓ Values will be migrated to the new location.[/green]")
                except Exception as e:
                    console.print(f"[red]Could not create directory:[/red] {e}")

        # Set defaults based on existing config
        default_arl = existing_config.get("deezer", {}).get("arl", "")
        default_folder = existing_config.get("downloads", {}).get("folder", "~/Music/Music Downloader")
        default_quality = str(existing_config.get("deezer", {}).get("quality", "1"))
        default_spotify_id = existing_config.get("spotify", {}).get("client_id", "")
        default_spotify_secret = existing_config.get("spotify", {}).get("client_secret", "")

        # 1. Deezer ARL
        console.print("\n[bold]Step 1: Deezer ARL[/bold] [red](required)[/red]")
        console.print("[dim]Your ARL is a cookie used to authenticate with Deezer.[/dim]")
        console.print("[dim]Find it here:[/dim] [link=https://github.com/nathom/streamrip/wiki/Finding-Your-Deezer-ARL-Cookie]streamrip wiki[/link]\n")
        
        arl = ""
        while not arl:
            arl = Prompt.ask("[cyan]Paste your Deezer ARL[/cyan]", default=default_arl).strip()
            if not arl:
                console.print("[red]ARL is required.[/red]")

        console.print("\n[yellow]Validating ARL...[/yellow]")
        if not _validate_deezer_arl(arl):
            console.print("[bold red]Warning:[/bold red] Could not validate ARL. It might be expired or invalid.")
            if not Confirm.ask("Continue anyway?", default=True):
                return
        else:
            console.print("[bold green]✓ ARL is valid![/bold green]")

        # 2. Download folder
        console.print("\n[bold]Step 2: Download Folder[/bold]")
        folder = Prompt.ask(
            f"[cyan]Download folder[/cyan]", 
            default=default_folder
        ).strip()

        # 3. Quality
        console.print("\n[bold]Step 3: Audio Quality[/bold]")
        console.print("  [bold white]1[/bold white] = 320kbps MP3 [dim](Standard)[/dim]")
        console.print("  [bold white]2[/bold white] = FLAC [dim](Lossless, requires paid Deezer)[/dim]")
        quality_str = Prompt.ask(
            "[cyan]Choose quality[/cyan]", 
            choices=["1", "2"], 
            default=default_quality
        )
        quality = int(quality_str)

        # 4. Spotify
        console.print("\n[bold]Step 4: Spotify Credentials[/bold] [dim](optional)[/dim]")
        console.print("[dim]MDL has built-in defaults, but you can provide your own.[/dim]")
        
        spotify_id = default_spotify_id
        spotify_secret = default_spotify_secret
        
        if Confirm.ask("[cyan]Add/Update custom Spotify credentials?[/cyan]", default=bool(spotify_id)):
            spotify_id = Prompt.ask("[cyan]Spotify Client ID[/cyan]", default=spotify_id).strip()
            spotify_secret = Prompt.ask("[cyan]Spotify Client Secret[/cyan]", default=spotify_secret, password=True).strip()

        config_content = _build_config_toml(arl, quality, folder, spotify_id, spotify_secret)
        
        try:
            modern_path.parent.mkdir(parents=True, exist_ok=True)
            with open(modern_path, "w", encoding="utf-8") as f:
                f.write(config_content)
            
            sr_path = ensure_streamrip_config_exists()
            merge_mdl_config_into_streamrip(sr_path, tomlkit.parse(config_content))
            
            console.print(f"\n[bold green]✓ Setup complete![/bold green]")
            console.print(f"[dim]Config saved to:[/dim] [cyan]{modern_path}[/cyan]")
            
            # If we migrated, suggest deleting the old one
            if existing_path and Path(existing_path) != modern_path:
                console.print(f"\n[yellow]Legacy config still exists at {existing_path}[/yellow]")
                if Confirm.ask("Delete the legacy config file?", default=False):
                    try:
                        os.remove(existing_path)
                        console.print("[green]✓ Legacy config deleted.[/green]")
                    except Exception as e:
                        console.print(f"[red]Error deleting file:[/red] {e}")

            console.print(f"\nTry: [bold white]mdl \"artist - track name\"[/bold white]\n")
        except Exception as e:
            console.print(f"\n[bold red]Error saving config:[/bold red] {e}")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Setup cancelled. Exiting...[/yellow]")
        return

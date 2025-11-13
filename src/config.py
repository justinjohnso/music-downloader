import sys
import os
from pathlib import Path
import tomlkit

# Import existing libraries
from streamrip.config import Config


def load_config() -> dict:
    """Load configuration from mdl-config.toml file."""
    config_path = Path.cwd() / "mdl-config.toml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return tomlkit.parse(f.read())
    return {}


def ensure_streamrip_config_exists() -> str:
    """Ensure the streamrip config file exists and return its path."""
    config_path = get_default_config_path()

    # Check if config file exists
    if not Path(config_path).exists():
        print(f"Streamrip config not found at {config_path}, creating default config...")
        try:
            # Create the config directory if it doesn't exist
            Path(config_path).parent.mkdir(parents=True, exist_ok=True)

            # Use streamrip's command to create the default config
            import subprocess
            result = subprocess.run(['rip', 'config', 'open'],
                                   capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and Path(config_path).exists():
                print(f"Created default streamrip config at {config_path}")
            else:
                raise Exception(f"rip config open failed: {result.stderr}")

        except Exception as e:
            print(f"Warning: Could not create default streamrip config: {e}")
            print("You may need to run 'rip config open' manually to create the config file.")
            # As a fallback, try to create an empty file
            try:
                Path(config_path).touch()
            except:
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


def apply_config_overrides(config: Config, config_data: dict) -> None:
    """
    Apply configuration overrides from mdl-config.toml to the streamrip config.

    This allows all streamrip configuration to be managed via mdl-config.toml file
    instead of being stored in the streamrip TOML config directly.

    Supported overrides include all streamrip configuration variables:
        - Credentials: deezer, qobuz, tidal, soundcloud, youtube sections
        - Downloads: downloads section
        - Artwork: artwork section
        - Metadata: metadata section
        - File paths: filepaths section
        - Conversions: conversions section
        - Database: database section
        - Filters: qobuz_filters section
        - CLI: cli section
        - LastFM: lastfm section
        - Misc: misc section

    Args:
        config: The loaded Config object to be modified
        config_data: The loaded configuration data from mdl-config.toml
    """

    # Debug: print what we're overriding
    if config_data:
        print(f"Applying config overrides from {len(config_data)} sections")

    # Apply configuration values from config_data to config.session
    # Session/Credentials - apply from config_data
    if "deezer" in config_data:
        deezer = config_data["deezer"]
        if deezer.get("arl") is not None:
            config.session.deezer.arl = deezer["arl"]
        if deezer.get("quality") is not None:
            config.session.deezer.quality = deezer["quality"]
        if deezer.get("use_deezloader") is not None:
            config.session.deezer.use_deezloader = deezer["use_deezloader"]
        if deezer.get("deezloader_warnings") is not None:
            config.session.deezer.deezloader_warnings = deezer["deezloader_warnings"]

    if "qobuz" in config_data:
        qobuz = config_data["qobuz"]
        if qobuz.get("email_or_userid") is not None:
            config.session.qobuz.email_or_userid = qobuz["email_or_userid"]
        if qobuz.get("password_or_token") is not None:
            config.session.qobuz.password_or_token = qobuz["password_or_token"]
        if qobuz.get("use_auth_token") is not None:
            config.session.qobuz.use_auth_token = qobuz["use_auth_token"]
        if qobuz.get("app_id") is not None:
            config.session.qobuz.app_id = qobuz["app_id"]
        if qobuz.get("quality") is not None:
            config.session.qobuz.quality = qobuz["quality"]
        if qobuz.get("download_booklets") is not None:
            config.session.qobuz.download_booklets = qobuz["download_booklets"]
        if qobuz.get("secrets") is not None:
            config.session.qobuz.secrets = qobuz["secrets"]

    if "tidal" in config_data:
        tidal = config_data["tidal"]
        if tidal.get("user_id") is not None:
            config.session.tidal.user_id = tidal["user_id"]
        if tidal.get("country_code") is not None:
            config.session.tidal.country_code = tidal["country_code"]
        if tidal.get("access_token") is not None:
            config.session.tidal.access_token = tidal["access_token"]
        if tidal.get("refresh_token") is not None:
            config.session.tidal.refresh_token = tidal["refresh_token"]
        if tidal.get("token_expiry") is not None:
            config.session.tidal.token_expiry = tidal["token_expiry"]
        if tidal.get("quality") is not None:
            config.session.tidal.quality = tidal["quality"]
        if tidal.get("download_videos") is not None:
            config.session.tidal.download_videos = tidal["download_videos"]

    if "soundcloud" in config_data:
        soundcloud = config_data["soundcloud"]
        if soundcloud.get("client_id") is not None:
            config.session.soundcloud.client_id = soundcloud["client_id"]
        if soundcloud.get("app_version") is not None:
            config.session.soundcloud.app_version = soundcloud["app_version"]
        if soundcloud.get("quality") is not None:
            config.session.soundcloud.quality = soundcloud["quality"]

    if "youtube" in config_data:
        youtube = config_data["youtube"]
        if youtube.get("video_downloads_folder") is not None:
            config.session.youtube.video_downloads_folder = youtube["video_downloads_folder"]
        if youtube.get("quality") is not None:
            config.session.youtube.quality = youtube["quality"]
        if youtube.get("download_videos") is not None:
            config.session.youtube.download_videos = youtube["download_videos"]

    # Top-level sections
    if "downloads" in config_data:
        downloads = config_data["downloads"]
        print(f"Setting downloads folder to: {downloads.get('folder')}")
        if downloads.get("folder") is not None:
            config.session.downloads.folder = os.path.expanduser(downloads["folder"])
            print(f"Downloads folder set to: {config.session.downloads.folder}")
        if downloads.get("source_subdirectories") is not None:
            config.session.downloads.source_subdirectories = downloads["source_subdirectories"]
        if downloads.get("disc_subdirectories") is not None:
            config.session.downloads.disc_subdirectories = downloads["disc_subdirectories"]
        if downloads.get("concurrency") is not None:
            config.session.downloads.concurrency = downloads["concurrency"]
        if downloads.get("max_connections") is not None:
            config.session.downloads.max_connections = downloads["max_connections"]
        if downloads.get("requests_per_minute") is not None:
            config.session.downloads.requests_per_minute = downloads["requests_per_minute"]
        if downloads.get("verify_ssl") is not None:
            config.session.downloads.verify_ssl = downloads["verify_ssl"]

    if "artwork" in config_data:
        artwork = config_data["artwork"]
        if artwork.get("embed") is not None:
            config.session.artwork.embed = artwork["embed"]
        if artwork.get("embed_size") is not None:
            config.session.artwork.embed_size = artwork["embed_size"]
        if artwork.get("embed_max_width") is not None:
            config.session.artwork.embed_max_width = artwork["embed_max_width"]
        if artwork.get("save_artwork") is not None:
            config.session.artwork.save_artwork = artwork["save_artwork"]
        if artwork.get("saved_max_width") is not None:
            config.session.artwork.saved_max_width = artwork["saved_max_width"]

    if "metadata" in config_data:
        metadata = config_data["metadata"]
        if metadata.get("set_playlist_to_album") is not None:
            config.session.metadata.set_playlist_to_album = metadata["set_playlist_to_album"]
        if metadata.get("renumber_playlist_tracks") is not None:
            config.session.metadata.renumber_playlist_tracks = metadata["renumber_playlist_tracks"]
        if metadata.get("exclude") is not None:
            config.session.metadata.exclude = metadata["exclude"]

    if "filepaths" in config_data:
        filepaths = config_data["filepaths"]
        if filepaths.get("add_singles_to_folder") is not None:
            config.session.filepaths.add_singles_to_folder = filepaths["add_singles_to_folder"]
        if filepaths.get("folder_format") is not None:
            config.session.filepaths.folder_format = filepaths["folder_format"]
        if filepaths.get("track_format") is not None:
            config.session.filepaths.track_format = filepaths["track_format"]
        if filepaths.get("restrict_characters") is not None:
            config.session.filepaths.restrict_characters = filepaths["restrict_characters"]
        if filepaths.get("truncate_to") is not None:
            config.session.filepaths.truncate_to = filepaths["truncate_to"]

    if "conversions" in config_data:
        conversions = config_data["conversions"]
        if conversions.get("enabled") is not None:
            config.session.conversion.enabled = conversions["enabled"]
        if conversions.get("codec") is not None:
            config.session.conversion.codec = conversions["codec"]
        if conversions.get("sampling_rate") is not None:
            config.session.conversion.sampling_rate = conversions["sampling_rate"]
        if conversions.get("bit_depth") is not None:
            config.session.conversion.bit_depth = conversions["bit_depth"]
        if conversions.get("lossy_bitrate") is not None:
            config.session.conversion.lossy_bitrate = conversions["lossy_bitrate"]

    if "qobuz_filters" in config_data:
        qobuz_filters = config_data["qobuz_filters"]
        if qobuz_filters.get("extras") is not None:
            config.session.qobuz_filters.extras = qobuz_filters["extras"]
        if qobuz_filters.get("repeats") is not None:
            config.session.qobuz_filters.repeats = qobuz_filters["repeats"]
        if qobuz_filters.get("non_albums") is not None:
            config.session.qobuz_filters.non_albums = qobuz_filters["non_albums"]
        if qobuz_filters.get("features") is not None:
            config.session.qobuz_filters.features = qobuz_filters["features"]
        if qobuz_filters.get("non_studio_albums") is not None:
            config.session.qobuz_filters.non_studio_albums = qobuz_filters["non_studio_albums"]
        if qobuz_filters.get("non_remaster") is not None:
            config.session.qobuz_filters.non_remaster = qobuz_filters["non_remaster"]

    if "database" in config_data:
        database = config_data["database"]
        if database.get("downloads_enabled") is not None:
            config.session.database.downloads_enabled = database["downloads_enabled"]
        if database.get("downloads_path") is not None:
            config.session.database.downloads_path = database["downloads_path"]
        if database.get("failed_downloads_enabled") is not None:
            config.session.database.failed_downloads_enabled = database["failed_downloads_enabled"]
        if database.get("failed_downloads_path") is not None:
            config.session.database.failed_downloads_path = database["failed_downloads_path"]

    if "lastfm" in config_data:
        lastfm = config_data["lastfm"]
        if lastfm.get("source") is not None:
            config.session.lastfm.source = lastfm["source"]
        if lastfm.get("fallback_source") is not None:
            config.session.lastfm.fallback_source = lastfm["fallback_source"]

    if "cli" in config_data:
        cli = config_data["cli"]
        if cli.get("text_output") is not None:
            config.session.cli.text_output = cli["text_output"]
        if cli.get("progress_bars") is not None:
            config.session.cli.progress_bars = cli["progress_bars"]
        if cli.get("max_search_results") is not None:
            config.session.cli.max_search_results = cli["max_search_results"]

    if "misc" in config_data:
        misc = config_data["misc"]
        if misc.get("version") is not None:
            config.session.misc.version = misc["version"]
        if misc.get("check_for_updates") is not None:
            config.session.misc.check_for_updates = misc["check_for_updates"]

    # Update the TOML representation to reflect our changes
    config.session.update_toml()

    # Sync session changes to file config so downloads use the overridden values
    config.file.downloads.folder = config.session.downloads.folder
    config.file.downloads.source_subdirectories = config.session.downloads.source_subdirectories
    config.file.downloads.disc_subdirectories = config.session.downloads.disc_subdirectories
    config.file.downloads.concurrency = config.session.downloads.concurrency
    config.file.downloads.max_connections = config.session.downloads.max_connections
    config.file.downloads.requests_per_minute = config.session.downloads.requests_per_minute
    config.file.downloads.verify_ssl = config.session.downloads.verify_ssl

    # Sync artwork settings
    config.file.artwork.embed = config.session.artwork.embed
    config.file.artwork.embed_size = config.session.artwork.embed_size
    config.file.artwork.embed_max_width = config.session.artwork.embed_max_width
    config.file.artwork.save_artwork = config.session.artwork.save_artwork
    config.file.artwork.saved_max_width = config.session.artwork.saved_max_width

    # Sync other sections as needed...

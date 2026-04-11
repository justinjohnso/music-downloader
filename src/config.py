import sys
import os
from pathlib import Path
import tomlkit


def load_config_with_path() -> tuple[dict, str | None]:
    """Load configuration from mdl-config.toml file, returning (data, path).

    Searches for the config file in the following order:
    1. Current working directory
    2. User's home directory
    3. Platform-specific config directory

    Returns:
        A tuple of (parsed config dict, path string) or ({}, None) if not found.
    """
    search_paths = [
        Path.cwd() / "mdl-config.toml",
        Path.home() / "mdl-config.toml",
    ]

    # Add platform-specific config directory
    if sys.platform == "darwin":  # macOS
        search_paths.append(
            Path.home() / "Library/Application Support/music-downloader/mdl-config.toml"
        )
    elif sys.platform == "win32":  # Windows
        search_paths.append(
            Path.home() / "AppData/Roaming/music-downloader/mdl-config.toml"
        )
    else:  # Linux and others
        search_paths.append(Path.home() / ".config/music-downloader/mdl-config.toml")

    for config_path in search_paths:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return tomlkit.parse(f.read()), str(config_path)
    return {}, None


def load_config() -> dict:
    """Load configuration from mdl-config.toml file.

    Searches for the config file in the following order:
    1. Current working directory
    2. User's home directory
    3. Platform-specific config directory
    """
    data, _ = load_config_with_path()
    return data


def get_backend_config(
    config_data: dict | None = None,
) -> tuple[str | None, str | None]:
    """Get optional backend Spotify resolve settings from mdl-config.toml.

    Args:
        config_data: Optional parsed config data. If omitted, config is loaded.

    Returns:
        Tuple of (resolve_url, api_key). Missing/blank values are returned as None.
    """
    if config_data is None:
        config_data = load_config()

    backend = config_data.get("backend", {})
    if not isinstance(backend, dict):
        return None, None

    resolve_url = backend.get("resolve_url")
    api_key = backend.get("api_key")

    if isinstance(resolve_url, str):
        resolve_url = resolve_url.strip() or None
    else:
        resolve_url = None

    if isinstance(api_key, str):
        api_key = api_key.strip() or None
    else:
        api_key = None

    return resolve_url, api_key


def ensure_streamrip_config_exists() -> str:
    """Ensure the streamrip config file exists and return its path.

    If the config file does not exist, creates parent directories and
    uses streamrip's set_user_defaults() to generate a default config
    with platform-specific values.

    Returns:
        The path to the streamrip config file.
    """
    from streamrip.config import set_user_defaults

    config_path = get_default_config_path()

    if not Path(config_path).exists():
        print(
            f"Streamrip config not found at {config_path}, creating default config..."
        )
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        set_user_defaults(config_path)
        print(f"Created default streamrip config at {config_path}")

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
    """Merge mdl-config.toml values into streamrip's config.toml on disk.

    Reads streamrip's config, patches matching sections/keys with values from
    mdl_config_data, and writes the result back. This ensures config.file and
    config.session start in sync when Config(path) is loaded afterwards.

    Only keys that already exist in streamrip's config are updated — no unknown
    keys are added. TOML formatting and comments are preserved via tomlkit.

    Args:
        streamrip_config_path: Path to streamrip's config.toml file.
        mdl_config_data: Parsed mdl-config.toml data (may be empty).
    """
    if not mdl_config_data:
        return

    # Sections whose names match between mdl-config and streamrip config
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
    }

    # Special mappings: mdl-config key -> streamrip config key
    SPECIAL_MAPPINGS = {
        "conversions": "conversion",
    }

    with open(streamrip_config_path, "r", encoding="utf-8") as f:
        sr_config = tomlkit.parse(f.read())

    for mdl_section, mdl_values in mdl_config_data.items():
        # Determine the target section name in streamrip config
        if mdl_section in MERGE_SECTIONS:
            sr_section = mdl_section
        elif mdl_section in SPECIAL_MAPPINGS:
            sr_section = SPECIAL_MAPPINGS[mdl_section]
        else:
            # Skip mdl-only sections (e.g. 'spotify', 'mdl')
            continue

        if sr_section not in sr_config:
            continue

        if not isinstance(mdl_values, dict):
            continue

        for key, value in mdl_values.items():
            if key in sr_config[sr_section]:
                # Never override streamrip's internal version marker
                if sr_section == "misc" and key == "version":
                    continue
                # Expand ~ in downloads.folder
                if mdl_section == "downloads" and key == "folder":
                    value = os.path.expanduser(value)
                sr_config[sr_section][key] = value

    with open(streamrip_config_path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(sr_config))


def _get_mdl_config_dir() -> Path:
    """Get the platform-specific mdl config directory."""
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/music-downloader"
    elif sys.platform == "win32":
        return Path.home() / "AppData/Roaming/music-downloader"
    else:
        return Path.home() / ".config/music-downloader"


def _validate_deezer_arl(arl: str) -> bool:
    """Attempt to validate a Deezer ARL by logging in."""
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
    backend_resolve_url: str = "",
    backend_api_key: str = "",
) -> str:
    """Build the mdl-config.toml content string."""
    lines = [
        "# Music Downloader Configuration",
        "# Edit this file or run 'mdl --setup' to reconfigure.",
        "",
        "[deezer]",
        f'arl = "{arl}"',
        f"quality = {quality}",
        "",
        "[downloads]",
        f'folder = "{folder}"',
        "",
        "[filepaths]",
        'track_format = "{artist} - {title}{explicit}"',
    ]

    if spotify_id and spotify_secret:
        lines.extend(
            [
                "",
                "[spotify]",
                f'client_id = "{spotify_id}"',
                f'client_secret = "{spotify_secret}"',
            ]
        )

    if backend_resolve_url and backend_api_key:
        lines.extend(
            [
                "",
                "[backend]",
                f'resolve_url = "{backend_resolve_url}"',
                f'api_key = "{backend_api_key}"',
            ]
        )

    return "\n".join(lines) + "\n"


def run_setup_wizard() -> None:
    """Interactive first-run setup wizard."""
    print("\n=== Music Downloader Setup ===\n")

    # 1. Deezer ARL
    print("Step 1: Deezer ARL (required)")
    print("Your Deezer ARL is an authentication cookie that lets you download music.")
    print(
        "Get it at: https://github.com/nathom/streamrip/wiki/Finding-Your-Deezer-ARL-Cookie"
    )
    print("ARLs expire every 3-4 months — you'll need to refresh it periodically.\n")

    arl = ""
    while not arl:
        arl = input("Paste your Deezer ARL: ").strip()
        if not arl:
            print("ARL is required to download music. Please paste it.")

    # Validate ARL by attempting login
    print("\nValidating ARL...")
    arl_valid = _validate_deezer_arl(arl)
    if not arl_valid:
        print("Warning: Could not validate ARL. It may be expired or invalid.")
        print(
            "Continuing anyway — you can update it later by running 'mdl --setup' again.\n"
        )
    else:
        print("ARL is valid!\n")

    # 2. Download folder
    default_folder = "~/Music/Music Downloader"
    print(f"Step 2: Download folder (default: {default_folder})")
    folder = input(f"Download folder [{default_folder}]: ").strip() or default_folder
    print()

    # 3. Quality
    print("Step 3: Audio quality")
    print("  1 = 320kbps MP3 (recommended)")
    print("  2 = FLAC lossless (requires paid Deezer)")
    quality_input = input("Quality [1]: ").strip() or "1"
    quality = int(quality_input) if quality_input in ("0", "1", "2") else 1
    print()

    # 4. Spotify (optional)
    print("Step 4: Spotify credentials (optional)")
    print(
        "Spotify credentials are optional and only used as your fallback if provided."
    )
    custom_spotify = (
        input("Add your own Spotify fallback credentials? [y/N]: ").strip().lower()
    )

    spotify_id = ""
    spotify_secret = ""
    if custom_spotify == "y":
        print("Get them at: https://developer.spotify.com/dashboard/")
        spotify_id = input("Spotify Client ID: ").strip()
        spotify_secret = input("Spotify Client Secret: ").strip()
    print()

    # Build config
    config_content = _build_config_toml(
        arl, quality, folder, spotify_id, spotify_secret
    )

    # Determine config path (platform-specific)
    config_path = _get_mdl_config_dir() / "mdl-config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    print(f"Config saved to: {config_path}")

    # Ensure streamrip config exists and merge settings
    sr_path = ensure_streamrip_config_exists()
    merge_mdl_config_into_streamrip(sr_path, tomlkit.parse(config_content))

    print(f"Streamrip config updated at: {sr_path}")
    print('\nSetup complete! Try: mdl "artist - track name"')

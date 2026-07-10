from unittest.mock import patch, MagicMock
from src.spotify import is_spotify_link, extract_spotify_info, get_spotify_tracks


def test_is_spotify_link():
    assert is_spotify_link("https://open.spotify.com/track/123") is True
    assert is_spotify_link("spotify:track:123") is True
    assert is_spotify_link("https://www.youtube.com/watch?v=123") is False
    assert is_spotify_link("just a string") is False


def test_extract_spotify_info():
    assert extract_spotify_info("https://open.spotify.com/track/123456") == ("123456", "track")
    assert extract_spotify_info("spotify:track:123456") == ("123456", "track")
    assert extract_spotify_info("https://open.spotify.com/playlist/789?si=abc") == ("789", "playlist")
    assert extract_spotify_info("spotify:album:abc") == ("abc", "album")


@patch("src.spotify.spotipy.Spotify")
@patch("src.config.load_config")
def test_get_spotify_tracks(mock_load_config, mock_spotify):
    # Setup mocks
    mock_load_config.return_value = {}
    mock_sp_instance = MagicMock()
    mock_spotify.return_value = mock_sp_instance
    
    mock_sp_instance.track.return_value = {
        "name": "Test Song",
        "artists": [{"name": "Test Artist"}],
    }

    # Execute
    tracks, info = get_spotify_tracks("https://open.spotify.com/track/123456")

    # Verify
    assert info["is_playlist"] is False
    assert info["name"] is None
    assert len(tracks) == 1
    assert tracks[0]["title"] == "Test Song"
    assert tracks[0]["artist"] == "Test Artist"
    
    # Ensure MemoryCacheHandler is being used when client is created
    # We can check the arguments passed to Spotify() via the patch
    args, kwargs = mock_spotify.call_args
    auth_manager = kwargs.get("auth_manager")
    assert auth_manager is not None
    assert auth_manager.cache_handler is not None

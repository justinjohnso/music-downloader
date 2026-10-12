from unittest.mock import patch, MagicMock

import pytest
from spotipy.exceptions import SpotifyException

from src.spotify import is_spotify_link, extract_spotify_info, get_spotify_tracks


def test_is_spotify_link():
    assert is_spotify_link("https://open.spotify.com/track/123") is True
    assert is_spotify_link("spotify:track:123") is True
    assert is_spotify_link("https://www.youtube.com/watch?v=123") is False
    assert is_spotify_link("just a string") is False


def test_extract_spotify_info():
    assert extract_spotify_info("https://open.spotify.com/track/123456") == (
        "123456",
        "track",
    )
    assert extract_spotify_info("spotify:track:123456") == ("123456", "track")
    assert extract_spotify_info("https://open.spotify.com/playlist/789?si=abc") == (
        "789",
        "playlist",
    )
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


@pytest.fixture()
def playlist_clients(monkeypatch):
    app = MagicMock()
    user = MagicMock()
    app.playlist.return_value = {"name": "Test Playlist"}
    user.playlist.return_value = {"name": "Test Playlist"}
    first_page = {
        "items": [
            {
                "track": {
                    "type": "track",
                    "name": "First",
                    "artists": [{"name": "Artist"}],
                }
            }
        ],
        "next": "next-page",
    }
    last_page = {
        "items": [
            {
                "item": {
                    "type": "track",
                    "name": "Second",
                    "artists": [{"name": "Artist"}],
                }
            }
        ],
        "next": None,
    }
    for client in (app, user):
        client.playlist_items.return_value = first_page
        client.next.return_value = last_page
    user_factory = MagicMock(return_value=user)
    monkeypatch.setattr(
        "src.config.load_config",
        lambda: {"spotify": {"client_id": "test", "client_secret": "test"}},
    )
    monkeypatch.setattr("src.spotify._get_spotify_app_client", lambda *_: app)
    monkeypatch.setattr("src.spotify._get_spotify_user_client", user_factory)
    return app, user, user_factory


def test_public_playlist_paginates_without_user_auth(playlist_clients):
    app, user, user_factory = playlist_clients
    tracks, info = get_spotify_tracks("spotify:playlist:test")
    assert tracks == [
        {"artist": "Artist", "title": "First"},
        {"artist": "Artist", "title": "Second"},
    ]
    assert info == {"is_playlist": True, "name": "Test Playlist"}
    app.next.assert_called_once()
    user_factory.assert_not_called()
    user.playlist.assert_not_called()


@pytest.mark.parametrize("status", [401, 403, 404])
@pytest.mark.parametrize("stage", ["playlist", "playlist_items", "next"])
def test_playlist_auth_failure_restarts_with_user_without_duplicates(
    playlist_clients, status, stage
):
    app, user, user_factory = playlist_clients
    getattr(app, stage).side_effect = SpotifyException(status, -1, "Access denied")
    tracks, info = get_spotify_tracks("spotify:playlist:test")
    assert tracks == [
        {"artist": "Artist", "title": "First"},
        {"artist": "Artist", "title": "Second"},
    ]
    assert info["name"] == "Test Playlist"
    user_factory.assert_called_once()
    user.next.assert_called_once()


@pytest.mark.parametrize("status", [429, 500])
def test_playlist_non_auth_errors_do_not_open_oauth(playlist_clients, status):
    app, _, user_factory = playlist_clients
    error = SpotifyException(status, -1, "Upstream failed for playlist 403404")
    app.playlist.side_effect = error
    with pytest.raises(SpotifyException) as caught:
        get_spotify_tracks("spotify:playlist:test")
    assert caught.value is error
    user_factory.assert_not_called()


def test_playlist_user_auth_failure_has_actionable_error(playlist_clients):
    app, user, _ = playlist_clients
    app.playlist.side_effect = SpotifyException(403, -1, "Access denied")
    user.playlist.side_effect = SpotifyException(401, -1, "Access denied")
    with pytest.raises(RuntimeError, match="re-authenticate") as caught:
        get_spotify_tracks("spotify:playlist:test")
    assert isinstance(caught.value.__cause__, SpotifyException)


def test_empty_playlist(playlist_clients):
    app, _, user_factory = playlist_clients
    app.playlist_items.return_value = {"items": [], "next": None}
    tracks, info = get_spotify_tracks("spotify:playlist:test")
    assert tracks == []
    assert info == {"is_playlist": True, "name": "Test Playlist"}
    user_factory.assert_not_called()


def test_playlist_skips_unavailable_tracks_and_episodes(playlist_clients):
    app, _, _ = playlist_clients
    app.playlist_items.return_value = {
        "items": [
            {"track": None},
            {"track": {"type": "episode"}},
            {"item": {"type": "track", "name": "Unknown", "artists": []}},
        ],
        "next": None,
    }
    tracks, _ = get_spotify_tracks("spotify:playlist:test")
    assert tracks == [{"artist": "Unknown Artist", "title": "Unknown"}]

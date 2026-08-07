import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import List, Dict, Any, Tuple

from app.errors import SpotifyAPIError, InvalidSpotifyLinkError

def get_spotify_client() -> spotipy.Spotify:
    client_id = os.environ.get("SPOTIPY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise SpotifyAPIError("Backend is not configured with Spotify credentials.")
        
    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def resolve_spotify_item(link_type: str, item_id: str) -> Tuple[bool, str, List[Dict[str, str]]]:
    sp = get_spotify_client()
    tracks = []
    is_playlist = False
    playlist_name = ""
    
    try:
        if link_type == "track":
            track_info = sp.track(item_id)
            if not track_info:
                raise InvalidSpotifyLinkError("Track not found")
                
            artist = track_info['artists'][0]['name']
            title = track_info['name']
            tracks.append({"artist": artist, "title": title})
            
        elif link_type == "album":
            album_info = sp.album(item_id)
            if not album_info:
                raise InvalidSpotifyLinkError("Album not found")
                
            for track in album_info['tracks']['items']:
                artist = track['artists'][0]['name']
                title = track['name']
                tracks.append({"artist": artist, "title": title})
                
        elif link_type == "playlist":
            is_playlist = True
            playlist_info = sp.playlist(item_id)
            if not playlist_info:
                raise InvalidSpotifyLinkError("Playlist not found")
                
            playlist_name = playlist_info['name']
            
            # Handle pagination
            results = sp.playlist_tracks(item_id)
            _extract_playlist_tracks(results['items'], tracks)
            
            while results['next']:
                results = sp.next(results)
                _extract_playlist_tracks(results['items'], tracks)
                
        else:
            raise InvalidSpotifyLinkError(f"Unsupported Spotify link type: {link_type}")
            
    except spotipy.SpotifyException as e:
        raise SpotifyAPIError(f"Spotify API error: {e}")
        
    return is_playlist, playlist_name, tracks

def _extract_playlist_tracks(items: List[Any], tracks: List[Dict[str, str]]) -> None:
    for item in items:
        track = item.get('track')
        if track:
            artist = track['artists'][0]['name']
            title = track['name']
            tracks.append({"artist": artist, "title": title})

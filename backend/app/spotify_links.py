import re
from typing import Optional, Tuple

def parse_spotify_link(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a Spotify URL and return (link_type, item_id).
    link_type can be 'track', 'album', or 'playlist'.
    """
    # Regex to match Spotify URLs and extract type and ID
    # Matches formats like:
    # https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT
    # https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
    # https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3
    pattern = r"https?://open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)"
    match = re.search(pattern, url)
    
    if match:
        return match.group(1), match.group(2)
        
    # Also support spotify URIs: spotify:track:4cOdK2wGLETKBW3PvgPWqT
    uri_pattern = r"spotify:(track|album|playlist):([a-zA-Z0-9]+)"
    uri_match = re.search(uri_pattern, url)
    if uri_match:
        return uri_match.group(1), uri_match.group(2)
        
    return None, None

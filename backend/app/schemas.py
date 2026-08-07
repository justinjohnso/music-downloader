from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class SpotifyResolveRequest(BaseModel):
    url: HttpUrl

class TrackData(BaseModel):
    artist: str
    title: str

class SpotifyResolveResponse(BaseModel):
    is_playlist: bool
    playlist_name: Optional[str] = None
    tracks: List[TrackData]

from pydantic import BaseModel


class SpotifyResolveRequest(BaseModel):
    spotify_link: str


class TrackData(BaseModel):
    artist: str
    title: str


class SpotifyResolveResponse(BaseModel):
    is_playlist: bool
    playlist_name: str | None = None
    tracks: list[TrackData]

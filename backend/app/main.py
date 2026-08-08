from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from app.errors import InvalidSpotifyLinkError, SpotifyAPIError
from app.schemas import SpotifyResolveRequest, SpotifyResolveResponse, TrackData
from app.security import get_api_key
from app.spotify_links import parse_spotify_link
from app.spotify_service import resolve_spotify_item

app = FastAPI(
    title="Spotify Auth Backend",
    description="Resolver service for music-downloader to fetch Spotify metadata",
    version="0.1.0",
)


@app.post("/spotify/resolve", response_model=SpotifyResolveResponse)
def resolve_link(request: SpotifyResolveRequest, api_key: str = Depends(get_api_key)):
    url_str = request.spotify_link
    link_type, item_id = parse_spotify_link(url_str)

    if not link_type or not item_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "code": "invalid_spotify_link",
                "message": "Invalid or unsupported Spotify link.",
            },
        )

    try:
        is_playlist, playlist_name, tracks_data = resolve_spotify_item(
            link_type, item_id
        )

        # Convert to Pydantic models
        tracks = [TrackData(artist=t["artist"], title=t["title"]) for t in tracks_data]

        return SpotifyResolveResponse(
            is_playlist=is_playlist, playlist_name=playlist_name, tracks=tracks
        )

    except InvalidSpotifyLinkError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SpotifyAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e!s}",
        )


@app.get("/health")
def health_check():
    return {"status": "ok"}

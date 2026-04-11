"""FastAPI application entrypoint for Spotify link resolution."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.errors import (
    get_error_code,
    map_error_to_http_exception,
    validate_spotify_link,
)
from app.schemas import ErrorResponse, SpotifyResolveRequest, SpotifyResolveResponse
from app.security import require_api_key
from app.spotify_service import resolve_spotify_link

app = FastAPI(title="Spotify Auth Backend")


@app.exception_handler(HTTPException)
async def http_exception_handler(_: object, exc: HTTPException) -> JSONResponse:
    """Return HTTP errors in the shared API error contract."""
    payload = ErrorResponse(
        detail=str(exc.detail),
        code=get_error_code(exc.status_code),
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.post(
    "/spotify/resolve",
    response_model=SpotifyResolveResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid Spotify link format"},
        401: {"model": ErrorResponse, "description": "Auth failure"},
        422: {"model": ErrorResponse, "description": "Unsupported Spotify link type"},
        500: {"model": ErrorResponse, "description": "Internal backend error"},
        502: {"model": ErrorResponse, "description": "Upstream Spotify API error"},
    },
)
def resolve_spotify(
    request: SpotifyResolveRequest,
    _: None = Depends(require_api_key),
) -> SpotifyResolveResponse:
    """Resolve a Spotify track/playlist link to normalized track metadata."""
    try:
        validate_spotify_link(request.spotify_link)
        return resolve_spotify_link(request.spotify_link)
    except Exception as error:
        raise map_error_to_http_exception(error) from error

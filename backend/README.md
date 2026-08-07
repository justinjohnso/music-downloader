# Spotify Auth Backend

FastAPI service for resolving Spotify track/playlist links into normalized metadata for the CLI app.

## Location

- Backend code: `backend/app/`
- Entrypoint: `backend/app/main.py`
- Endpoint: `POST /spotify/resolve`

## Local Setup

From repo root:

```bash
cd backend
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Request example:

```bash
curl -X POST http://127.0.0.1:8000/spotify/resolve \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-shared-key" \
  -d '{"spotify_link":"https://open.spotify.com/track/0aym2LBJBk9DAYuHHutrIl"}'
```

## Required Runtime Environment Variables

- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_BACKEND_API_KEY`

These are required by:
- `app.spotify_service` (Spotify credentials)
- `app.security` (API key guard via `X-API-Key`)

## Client Configuration

Configure `mdl-config.toml` in the root app:

```toml
[backend]
resolve_url = "https://your-domain.example.com/spotify/resolve"
api_key = "same-as-SPOTIFY_BACKEND_API_KEY"
```

Optional local fallback if backend is unavailable:

```toml
[spotify]
client_id = "your-local-spotify-client-id"
client_secret = "your-local-spotify-client-secret"
```

Resolution behavior in `src/spotify.py`:
1. Backend first (if `[backend]` values are set)
2. Local Spotipy fallback (if `[spotify]` values are set)
3. Error with setup guidance (if neither path is configured)

## GitHub Actions Secrets (Deploy + Runtime)

Expected secret set for VPS deployment:

### Deploy transport/auth
- `DO_VPS_HOST`
- `DO_VPS_USER`
- `DO_VPS_SSH_PRIVATE_KEY`
- `DO_VPS_SSH_PORT` (optional)

### Backend runtime
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_BACKEND_API_KEY`

## Deploy Assumptions

- Deployment target is an always-on DigitalOcean VPS.
- GitHub Actions performs deploy/update steps over SSH.
- Backend runs as a persistent service (for example, via systemd behind nginx in later deploy tasks).
- Secrets are managed in GitHub and injected at deploy/runtime; no secrets are committed in repo files.

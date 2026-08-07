# Deploy Artifacts (VPS)

This directory contains deployment artifacts for the Spotify auth backend.

## Included files

- `bootstrap-vps.sh`: installs system prerequisites, creates service user/directories, and prepares a Python virtual environment.
- `systemd/spotify-auth-backend.service`: runs `uvicorn` as a persistent systemd service on `127.0.0.1:8000`.
- `nginx/spotify-auth-backend.conf`: reverse-proxy site config forwarding HTTP traffic to the backend service.

## Typical setup flow

1. Run bootstrap as root:
   ```bash
   sudo bash deploy/bootstrap-vps.sh
   ```
2. Deploy backend code to `/opt/spotify-auth-backend/backend`.
3. Populate runtime env vars in `/etc/spotify-auth-backend/backend.env`.
4. Install and enable systemd service:
   ```bash
   sudo cp deploy/systemd/spotify-auth-backend.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now spotify-auth-backend.service
   ```
5. Install and enable nginx site:
   ```bash
   sudo cp deploy/nginx/spotify-auth-backend.conf /etc/nginx/sites-available/spotify-auth-backend.conf
   sudo ln -sf /etc/nginx/sites-available/spotify-auth-backend.conf /etc/nginx/sites-enabled/spotify-auth-backend.conf
   sudo nginx -t
   sudo systemctl reload nginx
   ```

Update `server_name` in `deploy/nginx/spotify-auth-backend.conf` to your domain before enabling the site.

#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "This script must be run as root (use sudo)." >&2
  exit 1
fi

APP_USER="${APP_USER:-spotify-auth}"
APP_GROUP="${APP_GROUP:-${APP_USER}}"
APP_ROOT="${APP_ROOT:-/opt/spotify-auth-backend}"
APP_DIR="${APP_DIR:-${APP_ROOT}/backend}"
VENV_DIR="${VENV_DIR:-${APP_ROOT}/.venv}"
ENV_DIR="${ENV_DIR:-/etc/spotify-auth-backend}"
ENV_FILE="${ENV_FILE:-${ENV_DIR}/backend.env}"
LOG_DIR="${LOG_DIR:-/var/log/spotify-auth-backend}"

echo "Installing system prerequisites..."
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  git \
  python3 \
  python3-dev \
  python3-pip \
  python3-venv \
  build-essential

if ! getent group "${APP_GROUP}" >/dev/null; then
  echo "Creating system group: ${APP_GROUP}"
  groupadd --system "${APP_GROUP}"
fi

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  echo "Creating system user: ${APP_USER}"
  useradd \
    --system \
    --gid "${APP_GROUP}" \
    --home-dir "${APP_ROOT}" \
    --create-home \
    --shell /usr/sbin/nologin \
    "${APP_USER}"
fi

install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${APP_ROOT}"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${APP_DIR}"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${LOG_DIR}"
install -d -o root -g "${APP_GROUP}" -m 0750 "${ENV_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  install -o root -g "${APP_GROUP}" -m 0640 /dev/null "${ENV_FILE}"
fi

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "Creating virtual environment: ${VENV_DIR}"
  python3 -m venv "${VENV_DIR}"
fi

echo "Installing backend runtime Python packages..."
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel
"${VENV_DIR}/bin/pip" install --upgrade fastapi spotipy uvicorn

echo ""
echo "Bootstrap complete."
echo "Next steps:"
echo "  1) Deploy backend code into: ${APP_DIR}"
echo "  2) Populate env vars in:      ${ENV_FILE}"
echo "  3) Install systemd unit and run:"
echo "       systemctl daemon-reload"
echo "       systemctl enable --now spotify-auth-backend.service"

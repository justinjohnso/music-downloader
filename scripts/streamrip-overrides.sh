#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBMODULE_DIR="$ROOT_DIR/vendor/streamrip"
PATCH_DIR="$ROOT_DIR/vendor/streamrip-patches"
PATCH_FILE="$PATCH_DIR/0001-local-overrides.patch"

usage() {
  cat <<'EOF'
Usage: scripts/streamrip-overrides.sh <command>

Commands:
  status   Show submodule status and patch applicability.
  export   Export current vendor/streamrip local changes to patch file.
  apply    Apply patch file to a clean vendor/streamrip checkout.
  check    Check whether patch file can be applied cleanly.
EOF
}

require_submodule() {
  if [[ ! -e "$SUBMODULE_DIR/.git" ]]; then
    echo "error: vendor/streamrip is not initialized."
    echo "run: git submodule update --init --recursive"
    exit 1
  fi
}

status_cmd() {
  require_submodule
  echo "Submodule HEAD:"
  git -C "$SUBMODULE_DIR" --no-pager log -1 --oneline
  echo
  echo "Submodule working tree:"
  git -C "$SUBMODULE_DIR" --no-pager status --short || true
  echo
  if [[ -f "$PATCH_FILE" ]]; then
    echo "Patch file: $PATCH_FILE"
    if git -C "$SUBMODULE_DIR" apply --check "$PATCH_FILE" >/dev/null 2>&1; then
      echo "Patch check: can apply"
    elif git -C "$SUBMODULE_DIR" apply --reverse --check "$PATCH_FILE" >/dev/null 2>&1; then
      echo "Patch check: already applied (or mostly applied)"
    else
      echo "Patch check: does not apply cleanly"
    fi
  else
    echo "Patch file not found: $PATCH_FILE"
  fi
}

export_cmd() {
  require_submodule
  mkdir -p "$PATCH_DIR"
  git -C "$SUBMODULE_DIR" diff --binary >"$PATCH_FILE"
  if [[ ! -s "$PATCH_FILE" ]]; then
    rm -f "$PATCH_FILE"
    echo "No local submodule changes found; nothing exported."
    exit 0
  fi
  echo "Exported patch: $PATCH_FILE"
}

check_cmd() {
  require_submodule
  if [[ ! -f "$PATCH_FILE" ]]; then
    echo "error: patch file not found: $PATCH_FILE"
    exit 1
  fi
  if git -C "$SUBMODULE_DIR" apply --check "$PATCH_FILE" >/dev/null 2>&1; then
    echo "Patch applies cleanly."
    exit 0
  fi
  if git -C "$SUBMODULE_DIR" apply --reverse --check "$PATCH_FILE" >/dev/null 2>&1; then
    echo "Patch appears to already be applied."
    exit 0
  fi
  echo "Patch does not apply cleanly."
  exit 1
}

apply_cmd() {
  require_submodule
  if [[ ! -f "$PATCH_FILE" ]]; then
    echo "error: patch file not found: $PATCH_FILE"
    exit 1
  fi
  if [[ -n "$(git -C "$SUBMODULE_DIR" status --porcelain)" ]]; then
    echo "error: vendor/streamrip has uncommitted changes."
    echo "clean it first before applying patch."
    exit 1
  fi
  git -C "$SUBMODULE_DIR" apply --3way "$PATCH_FILE"
  echo "Applied patch to vendor/streamrip."
}

main() {
  if [[ $# -ne 1 ]]; then
    usage
    exit 1
  fi

  case "$1" in
    status) status_cmd ;;
    export) export_cmd ;;
    apply) apply_cmd ;;
    check) check_cmd ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"

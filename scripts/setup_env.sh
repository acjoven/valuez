#!/usr/bin/env bash
#
# Idempotent bootstrap for the valuez development environment.
#
# Used by .cursor/environment.json:
#   install -> `bash scripts/setup_env.sh install`  (full, build-time setup)
#   start   -> `bash scripts/setup_env.sh ensure`   (per-boot self-heal)
#
# It (re)creates the gitignored virtualenv at .venv with:
#   - the sibling `dotz` toolkit installed editable (storage / query / graph),
#   - valuez's runtime + test dependencies, and
#   - `click<8.2` pinned (typer 0.12.5 is incompatible with click>=8.2).
#
# Running it by hand is the fastest way to recover after a fresh VM wipes .venv:
#   bash scripts/setup_env.sh
#
set -euo pipefail

# Repo root (this script lives in <root>/scripts/), independent of the caller's cwd.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv"
PY="$VENV/bin/python"

log() { printf '[setup_env] %s\n' "$*"; }

# Locate the sibling `dotz` repository. Override with DOTZ_DIR; the local checkout
# dir may be named `dotz` (canonical) or `dots` (legacy clone dir) -- both work.
find_dotz() {
  local candidates=("${DOTZ_DIR:-}" "$ROOT/../dotz" "$ROOT/../dots")
  local c
  for c in "${candidates[@]}"; do
    if [[ -n "$c" && -f "$c/pyproject.toml" ]]; then
      (cd "$c" && pwd)
      return 0
    fi
  done
  return 1
}

# True when the venv exists and can import both valuez and dotz.
venv_ok() {
  [[ -x "$PY" ]] || return 1
  (cd "$ROOT" && "$PY" - <<'PYEOF' >/dev/null 2>&1
import valuez            # repo root import (run from ROOT)
import dotz.storage      # the sibling toolkit must be importable
PYEOF
  )
}

full_setup() {
  if [[ ! -x "$PY" ]]; then
    log "creating virtualenv at .venv"
    python3 -m venv "$VENV"
  fi
  log "upgrading pip"
  "$PY" -m pip install -q --upgrade pip
  if dotz_dir="$(find_dotz)"; then
    log "installing sibling dotz, editable, from $dotz_dir"
    "$PY" -m pip install -q -e "$dotz_dir"
  else
    log "WARNING: sibling 'dotz' repo not found (checked \$DOTZ_DIR, ../dotz, ../dots)."
    log "         valuez.repository/graph need it; set DOTZ_DIR to the dotz checkout."
  fi
  log "installing valuez requirements"
  "$PY" -m pip install -q -r "$ROOT/requirements.txt"
  log "pinning click<8.2 (typer 0.12.5 compatibility)"
  "$PY" -m pip install -q "click<8.2"
}

MODE="${1:-install}"
case "$MODE" in
  ensure)
    if venv_ok; then
      log "environment already healthy; nothing to do"
      exit 0
    fi
    log "environment missing or broken; rebuilding"
    full_setup
    ;;
  install)
    full_setup
    ;;
  *)
    echo "usage: $0 [install|ensure]" >&2
    exit 2
    ;;
esac

if venv_ok; then
  log "valuez environment ready: $PY"
else
  echo "[setup_env] ERROR: environment verification failed (import valuez / dotz.storage)" >&2
  exit 1
fi

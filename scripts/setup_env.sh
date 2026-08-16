#!/usr/bin/env bash
#
# Idempotent bootstrap for the valuez development environment.
#
# Used by .cursor/environment.json:
#   install -> `bash scripts/setup_env.sh install`  (full, build-time setup)
#   start   -> `bash scripts/setup_env.sh ensure`   (per-boot self-heal)
#
# It (re)creates the gitignored virtualenv at .venv with:
#   - the sibling `dots` toolkit installed editable (it packages as `dotz`),
#   - valuez's runtime + test dependencies,
#   - `click<8.2` pinned (typer 0.12.5 is incompatible with click>=8.2), and
#   - a venv-level `dots` -> `dotz` import alias (see the "gotcha" in AGENTS.md).
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

# Locate the sibling `dots` repository (packaged as `dotz`). Override with DOTS_DIR.
find_dots() {
  local candidates=("${DOTS_DIR:-}" "$ROOT/../dots" "$ROOT/../dotz")
  local c
  for c in "${candidates[@]}"; do
    if [[ -n "$c" && -f "$c/pyproject.toml" ]]; then
      (cd "$c" && pwd)
      return 0
    fi
  done
  return 1
}

# True when the venv exists and can import both valuez and the aliased `dots`.
venv_ok() {
  [[ -x "$PY" ]] || return 1
  (cd "$ROOT" && "$PY" - <<'PYEOF' >/dev/null 2>&1
import valuez            # repo root import (run from ROOT)
import dots.storage      # the dots -> dotz alias must be active
PYEOF
  )
}

# Write the venv-level `dots` -> `dotz` alias so `import dots.*` resolves to dotz.
ensure_alias() {
  "$PY" - <<'PYEOF'
import os
import site

alias = (
    "import sys, importlib, importlib.util; "
    "sys.modules.__setitem__('dots', importlib.import_module('dotz')) "
    "if importlib.util.find_spec('dotz') and importlib.util.find_spec('dots') is None "
    "else None\n"
)
targets = list(site.getsitepackages())
try:
    targets.append(site.getusersitepackages())
except Exception:
    pass
for d in targets:
    try:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "zz_dots_to_dotz_compat.pth"), "w", encoding="utf-8") as f:
            f.write(alias)
        break
    except OSError:
        continue
PYEOF
}

full_setup() {
  if [[ ! -x "$PY" ]]; then
    log "creating virtualenv at .venv"
    python3 -m venv "$VENV"
  fi
  log "upgrading pip"
  "$PY" -m pip install -q --upgrade pip
  if dots_dir="$(find_dots)"; then
    log "installing sibling dots (as dotz), editable, from $dots_dir"
    "$PY" -m pip install -q -e "$dots_dir"
  else
    log "WARNING: sibling 'dots' repo not found (checked \$DOTS_DIR, ../dots, ../dotz)."
    log "         valuez.repository/graph need it; set DOTS_DIR to the dots checkout."
  fi
  log "installing valuez requirements"
  "$PY" -m pip install -q -r "$ROOT/requirements.txt"
  log "pinning click<8.2 (typer 0.12.5 compatibility)"
  "$PY" -m pip install -q "click<8.2"
  log "writing dots -> dotz venv alias"
  ensure_alias
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
  echo "[setup_env] ERROR: environment verification failed (import valuez / dots.storage)" >&2
  exit 1
fi

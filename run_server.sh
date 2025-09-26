#!/usr/bin/env bash
set -euo pipefail

# ----------------------------
# Config you can tweak
# ----------------------------
APP_MODULE="${APP_MODULE:-app.main:app}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:---reload}"             # set to "" in prod to disable reload
VENV_DIR="${VENV_DIR:-venv}"
REQ_FILE="${REQ_FILE:-requirements.txt}" # root requirements for server+client
# ----------------------------

# Pick Python
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "❌ No python interpreter found. Please install Python 3.10+." >&2
  exit 1
fi

# Create venv if missing
if [[ ! -d "${VENV_DIR}" ]]; then
  echo "📦 Creating virtualenv: ${VENV_DIR}"
  "${PY}" -m venv "${VENV_DIR}"
fi

# Activate venv
# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

# Upgrade pip toolchain (quiet)
python -m pip install --upgrade pip setuptools wheel >/dev/null

# Install dependencies
if [[ -f "${REQ_FILE}" ]]; then
  echo "📚 Installing dependencies from ${REQ_FILE}"
  pip install -r "${REQ_FILE}"
else
  echo "ℹ️  ${REQ_FILE} not found. Installing minimal deps (FastAPI + ORM + NL→SQL model)."
  pip install uvicorn fastapi "sqlalchemy>=2" pydantic transformers safetensors sentencepiece torch
fi

# Sanity check: uvicorn
if ! command -v uvicorn >/dev/null 2>&1; then
  echo "❌ uvicorn not found after install" >&2
  exit 1
fi

# Optional: verify torch is importable (useful for /ask endpoint)
if python - <<'PY' >/dev/null 2>&1; then
import importlib
importlib.import_module("torch")
PY
  : # ok
else
  echo "⚠️  PyTorch couldn't be imported. If you're on macOS, try:"
  echo "    pip install torch"
  echo "   (For CUDA, install torch from the CUDA-specific index URL.)"
fi

# Make project importable
export PYTHONPATH="."

# NL→SQL model env (used by your model loader)
export NLSQL_MODEL_ID="${NLSQL_MODEL_ID:-chatdb/natural-sql-7b}"
export NLSQL_MAX_NEW_TOKENS="${NLSQL_MAX_NEW_TOKENS:-400}"

echo "🚀 Starting server on http://${HOST}:${PORT}  (module: ${APP_MODULE})"
exec uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}" ${RELOAD}

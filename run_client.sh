#!/usr/bin/env bash
set -euo pipefail

CLIENT_DIR="${CLIENT_DIR:-client}"
ENTRY="${ENTRY:-streamlit_app.py}"     # root entry file
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

# activate root venv if present
if [[ -d "venv" ]]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
fi

# make client/ importable for pages/*
export PYTHONPATH="$(pwd)/${CLIENT_DIR}:${PYTHONPATH:-}"

cd "${CLIENT_DIR}"

# load .env if present
if [[ -f ".env" ]]; then
  set -a; source ".env"; set +a
fi
export API_BASE_URL

echo "🧑‍💻 Starting Streamlit client (API_BASE_URL=${API_BASE_URL})"
exec streamlit run "${ENTRY}"

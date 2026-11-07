#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

CONTEXT="${1:-chemcollective-coolant}"
SURFACE="${2:-auto}"
PORT="${PORT:-8765}"

if [ ! -f .env ]; then
  echo "Missing .env: copy .env.example to .env and set HAI_API_KEY." >&2
  exit 1
fi

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use. Stop the other Jesse first, or run PORT=8766 ./launch_local.sh" >&2
  exit 1
fi

uv sync --quiet

if [ ! -x ui/node_modules/.bin/vite ]; then
  echo "Installing UI dependencies..."
  (cd ui && pnpm install --frozen-lockfile)
fi

echo "Building the UI..."
(cd ui && ./node_modules/.bin/tsc -b && ./node_modules/.bin/vite build --logLevel warn)

(sleep 2 && open "http://127.0.0.1:$PORT") >/dev/null 2>&1 &

exec uv run --env-file .env jesse-ui --context "$CONTEXT" --surface "$SURFACE" --port "$PORT"

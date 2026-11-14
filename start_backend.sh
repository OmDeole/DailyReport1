#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
elif [ -f "./.venv/bin/python" ]; then
    PYTHON="./.venv/bin/python"
else
    PYTHON="python3"
fi

echo "=============================================================================="
echo " Starting Django Backend with Waitress WSGI Server on http://127.0.0.1:8000"
echo "=============================================================================="

"$PYTHON" manage.py migrate --noinput
"$PYTHON" manage.py collectstatic --noinput

"$PYTHON" -m waitress --listen=127.0.0.1:8000 daily_report_backend.wsgi:application


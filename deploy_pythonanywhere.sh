#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/kimmins/serviceproject"
WSGI_FILE="/var/www/kimmins_pythonanywhere_com_wsgi.py"

cd "$PROJECT_DIR"
git pull origin master
source .venv/bin/activate
pip install -r requirements.txt
touch "$WSGI_FILE"

echo "Deploy complete: https://kimmins.pythonanywhere.com"

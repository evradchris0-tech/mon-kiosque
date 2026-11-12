#!/bin/sh
# Prépare le dossier deploy_vercel/ (code backend + appli + config), prêt pour `vercel deploy --prod`.
set -e
cd "$(dirname "$0")"
rm -rf deploy_vercel/backend deploy_vercel/prompts deploy_vercel/api deploy_vercel/index.py deploy_vercel/vercel.json
mkdir -p deploy_vercel/backend
cp -r backend/app deploy_vercel/backend/app
cp -r prompts deploy_vercel/prompts
find deploy_vercel -name __pycache__ -type d -prune -exec rm -rf {} +
cat > deploy_vercel/index.py <<'PY'
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from app.api.main import creer_app  # noqa: E402

app = creer_app()
PY
cat > deploy_vercel/requirements.txt <<'REQ'
fastapi>=0.115
pydantic>=2.9
pydantic-settings>=2.5
sqlalchemy>=2.0.36
httpx>=0.27
fpdf2>=2.8
qrcode>=7.4
pillow>=10
python-multipart>=0.0.9
REQ
echo "3.12" > deploy_vercel/.python-version
cat > deploy_vercel/vercel.json <<'JSON'
{
  "functions": { "index.py": { "maxDuration": 60, "includeFiles": "{backend,prompts}/**" } }
}
JSON
echo "deploy_vercel/ prêt"

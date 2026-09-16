#!/bin/bash
set -e

echo "=== Vercel Build: Preparing static files ==="
mkdir -p staticfiles

echo "=== Installing dependencies for static collection ==="
python3 -m pip install -r requirements.txt --target .vendor

export PYTHONPATH="$(pwd)/.vendor:${PYTHONPATH}"

echo "=== Collecting static files ==="
python3 manage.py collectstatic --noinput --clear

echo "=== Cleaning up temporary build files ==="
rm -rf .vendor

echo "=== Static files successfully collected ==="
ls -la staticfiles/ || true
echo "=== Vercel build complete ==="

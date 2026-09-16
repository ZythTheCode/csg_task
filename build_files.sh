#!/bin/bash
# Vercel deployment build script
echo "=== Installing dependencies for Vercel ==="
python3 -m pip install -r requirements.txt

echo "=== Collecting static files ==="
python3 manage.py collectstatic --noinput --clear

echo "=== Vercel build complete ==="

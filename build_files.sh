#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies using uv if available, or pip with PEP 668 bypass
if command -v uv >/dev/null 2>&1; then
    echo "Installing requirements with uv..."
    uv pip install -r requirements.txt --system
elif python3 -m pip install --help | grep -q -- '--break-system-packages'; then
    echo "Installing requirements with pip (--break-system-packages)..."
    python3 -m pip install -r requirements.txt --break-system-packages
else
    echo "Installing requirements with standard pip..."
    python3 -m pip install -r requirements.txt
fi

# Run migrations if DATABASE_URL is available
if [ -n "$DATABASE_URL" ]; then
    echo "DATABASE_URL detected. Running database migrations..."
    python3 manage.py migrate --no-input
fi

# Collect static files into staticfiles_build/static
echo "Collecting static files..."
python3 manage.py collectstatic --no-input --clear

echo "Vercel build completed successfully."

#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing requirements..."
if command -v uv >/dev/null 2>&1; then
    uv pip install -r requirements.txt
else
    pip install -r requirements.txt
fi

# Run migrations if DATABASE_URL is available
if [ -n "$DATABASE_URL" ]; then
    echo "DATABASE_URL detected. Running database migrations..."
    python manage.py migrate --no-input
fi

# Collect static files into staticfiles_build/static
echo "Collecting static files..."
python manage.py collectstatic --no-input --clear

echo "Vercel build completed successfully."

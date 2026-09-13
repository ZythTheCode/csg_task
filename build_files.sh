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

# Ensure build output directory exists
mkdir -p staticfiles_build/static

# Collect static files into staticfiles_build/static
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Ensure custom static files are present in the CDN output directory
if [ -d "static" ]; then
    echo "Syncing custom static files to staticfiles_build/static..."
    cp -r static/* staticfiles_build/static/
fi

echo "Verifying output directory..."
ls -la staticfiles_build
ls -la staticfiles_build/static

echo "Vercel build completed successfully."

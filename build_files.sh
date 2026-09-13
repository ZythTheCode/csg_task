#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
python3 -m pip install -r requirements.txt

# Run migrations if DATABASE_URL is available
if [ -n "$DATABASE_URL" ]; then
    echo "DATABASE_URL detected. Running database migrations..."
    python3 manage.py migrate --no-input
fi

# Collect static files into staticfiles_build/static
echo "Collecting static files..."
python3 manage.py collectstatic --no-input --clear

echo "Vercel build completed successfully."

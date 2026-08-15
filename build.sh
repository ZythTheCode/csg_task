#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Create cache directory for file-based caching
mkdir -p django_cache

python manage.py collectstatic --no-input --clear
python manage.py migrate
python manage.py create_superadmin

echo "Build script completed successfully."

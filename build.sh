#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Seed data without overwriting existing user profile photos or uploaded media
python manage.py seed_data || echo "Seed data skipped or already loaded"

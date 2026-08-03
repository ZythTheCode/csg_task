#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Seed initial data only if SEED_DATA environment variable is set to "true"
if [ "$SEED_DATA" = "true" ]; then
    echo "SEED_DATA=true detected. Seeding initial database..."
    python manage.py seed_data || echo "Seed data failed or already loaded"
else
    echo "SEED_DATA is not set to 'true'. Skipping seed_data for persistent live environment."
fi


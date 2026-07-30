#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Load local data fixture if it exists and DB is empty
python manage.py loaddata fixtures/data.json || echo "Fixture load skipped or already loaded"

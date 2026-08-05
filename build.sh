#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input --clear
python manage.py migrate

echo "Build script completed successfully."

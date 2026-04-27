#!/bin/bash
set -e

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_db
celery -A playto worker --beat --loglevel=info --concurrency=2 &
gunicorn playto.wsgi --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --access-logfile - --log-level debug

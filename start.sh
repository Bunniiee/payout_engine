#!/bin/bash
set -e

python manage.py collectstatic --no-input
python manage.py migrate
celery -A playto worker --beat --loglevel=info --concurrency=2 &
gunicorn playto.wsgi --bind 0.0.0.0:$PORT --workers 2

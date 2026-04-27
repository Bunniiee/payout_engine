web: python manage.py collectstatic --no-input && python manage.py migrate && gunicorn playto.wsgi --bind 0.0.0.0:$PORT --workers 2
worker: celery -A playto worker --loglevel=info --concurrency=2
beat: celery -A playto beat --loglevel=info

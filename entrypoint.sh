#!/bin/sh
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput --settings=horison.settings

echo "Starting Gunicorn..."
exec gunicorn horison.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 3 \
    --timeout 120

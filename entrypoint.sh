#!/bin/sh
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput --settings=horison.settings

if [ -n "\${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "\${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "\${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  echo "Ensuring Django superuser exists..."
  python manage.py createsuperuser --noinput --settings=horison.settings || true
fi

echo "Starting Gunicorn..."
exec gunicorn horison.wsgi:application \
    --bind 0.0.0.0:\${PORT:-8000} \
    --workers 3 \
    --timeout 120

FROM python:3.12-slim

# ============================================
# Dépendances système : GDAL, GEOS, PROJ, PostgreSQL client
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    proj-data \
    proj-bin \
    libpq-dev \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Variables nécessaires pour que pip trouve gdal-config au bon endroit
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /app

# Installer les dépendances Python d'abord (meilleur cache Docker)
COPY requirements.txt .

# GDAL Python doit correspondre à la version système installée par apt.
# On récupère automatiquement la version système pour éviter tout conflit.
RUN GDAL_VERSION=$(gdal-config --version) && \
    pip install --no-cache-dir GDAL==$GDAL_VERSION && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Collecte des fichiers statiques au build (whitenoise les servira)
RUN python manage.py collectstatic --noinput --settings=horison.settings || true

EXPOSE 8000

# entrypoint.sh gère les migrations avant de lancer gunicorn
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

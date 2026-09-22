"""
Django settings for horison project - Production-ready version.
"""
import os
from pathlib import Path
import dj_database_url
 
BASE_DIR = Path(__file__).resolve().parent.parent
 
# ============================================
# GDAL / GEOS / PROJ
# Sous Linux (Docker), ces bibliothèques sont installées au niveau
# système (apt-get install gdal-bin libgdal-dev). Pas besoin de chemins
# codés en dur : Django/GDAL les trouve automatiquement si les paquets
# système sont présents. On ne force les chemins que si des variables
# d'environnement optionnelles sont fournies.
# ============================================
GDAL_LIBRARY_PATH = os.getenv('GDAL_LIBRARY_PATH')  # optionnel
GEOS_LIBRARY_PATH = os.getenv('GEOS_LIBRARY_PATH')  # optionnel
 
# ============================================
# SECURITY
# ============================================
SECRET_KEY = os.environ['SECRET_KEY']  # obligatoire, pas de valeur par défaut
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',') if os.getenv('ALLOWED_HOSTS') else []
 
# ============================================
# APPLICATIONS
# ============================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'authentication',
    'geoportail',
    'agriculture',
    'cartotheque',
]
 
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # fichiers statiques en prod
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
 
# ============================================
# CORS - restreint au(x) domaine(s) du frontend Next.js
# ============================================
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if os.getenv('CORS_ALLOWED_ORIGINS') else []
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
]
 
ROOT_URLCONF = 'horison.urls'
 
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
 
WSGI_APPLICATION = 'horison.wsgi.application'
 
# ============================================
# DATABASE
# DATABASE_URL fourni automatiquement par Railway au format :
# postgres://user:password@host:port/dbname
# ============================================
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        engine='django.contrib.gis.db.backends.postgis',
        conn_max_age=600,
    )
}
 
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
 
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
 
# ============================================
# STATIC / MEDIA
# ============================================
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
 
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
 
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # AllowAny -> à restreindre en prod
    ],
}
 
# ============================================
# EMAIL (alertes)
# Toutes les valeurs viennent de l'environnement — ne JAMAIS coder
# un mot de passe en dur dans ce fichier.
# ============================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
ALERT_RECIPIENT_EMAIL = os.getenv('ALERT_RECIPIENT_EMAIL', '')
 
NDVI_ALERT_THRESHOLD = float(os.getenv('NDVI_ALERT_THRESHOLD', '0.35'))
 
# ============================================
# GOOGLE EARTH ENGINE
# Clé de service à fournir en base64 dans la variable d'environnement,
# décodée au démarrage de l'app (voir docs de déploiement).
# ============================================
GEE_SERVICE_ACCOUNT_KEY_B64 = os.getenv('GEE_SERVICE_ACCOUNT_KEY_B64', '')
 
"""
Django settings for horison project.

Les valeurs sensibles (clé secrète, mots de passe, SMTP…) sont lues depuis
les variables d'environnement ou depuis un fichier `.env` à la racine du
projet (voir `.env.exemple`).
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


# ============================================
# CONFIGURATION GIS (DOIT ÊTRE EN HAUT)
# ============================================
# Sous Windows, GDAL/GEOS/PROJ sont fournis par la roue Python "GDAL"
# installée dans le venv (dossier site-packages/osgeo). Sous Linux (serveur),
# Django trouve les bibliothèques système tout seul : on ne touche à rien.

os.environ.setdefault('PROJ_NETWORK', 'OFF')

if os.name == 'nt':
    osgeo_path = Path(sys.prefix) / 'Lib' / 'site-packages' / 'osgeo'

    proj_path = osgeo_path / 'data' / 'proj'
    if (proj_path / 'proj.db').exists():
        os.environ['PROJ_LIB'] = str(proj_path)

    gdal_data_path = osgeo_path / 'data' / 'gdal'
    if gdal_data_path.exists():
        os.environ['GDAL_DATA'] = str(gdal_data_path)

    if osgeo_path.exists():
        os.environ['PATH'] = str(osgeo_path) + os.pathsep + os.environ['PATH']

    if (osgeo_path / 'gdal.dll').exists():
        GDAL_LIBRARY_PATH = str(osgeo_path / 'gdal.dll')
    if (osgeo_path / 'geos_c.dll').exists():
        GEOS_LIBRARY_PATH = str(osgeo_path / 'geos_c.dll')

# ============================================
# SÉCURITÉ
# ============================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-only-a-remplacer-en-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DEBUG', False)

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')

# ============================================
# APPLICATION DEFINITION
# ============================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework.authtoken',
    'django.contrib.gis',
    'rest_framework',
    'authentication',
    'geoportail',
    'corsheaders',  # <-- IMPORTANT: Doit être ici
    'agriculture',
    
    'cartotheque', 

]

# MIDDLEWARE - CORRIGÉ
# ============================================

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # <-- DOIT ÊTRE EN PREMIER
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ============================================
# CORS CONFIGURATION - CORRIGÉ
# ============================================

# OPTION 1: Pour le développement, autoriser toutes les origines (plus simple)
CORS_ALLOW_ALL_ORIGINS = True

# OPTION 2: Ou spécifiquement autoriser localhost:3001
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3001",
#     "http://127.0.0.1:3001",
#     "http://localhost:3000",
#     "http://127.0.0.1:3000",
# ]

# Autres paramètres CORS importants
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ============================================
# AUTRES CONFIGURATIONS
# ============================================

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
# ============================================

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('DB_NAME', 'Ecommune'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '1234'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# ============================================
# PASSWORD VALIDATION
# ============================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ============================================
# INTERNATIONALIZATION
# ============================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ============================================
# STATIC FILES
# ============================================

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
X_FRAME_OPTIONS = "ALLOW-FROM http://localhost:3001"

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

 # --- CONFIGURATION EMAIL (Pour les alertes) ---
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')  # Votre email d'envoi
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')  # Mot de passe d'application Gmail
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# L'adresse email qui reçoit les alertes (Contrôlée par vous)
ALERT_RECIPIENT_EMAIL = os.environ.get('ALERT_RECIPIENT_EMAIL', '')

# Seuil NDVI pour déclencher une alerte (ex: < 0.35 = Stress hydrique sévère)
NDVI_ALERT_THRESHOLD = 0.35

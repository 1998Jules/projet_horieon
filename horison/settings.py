"""
Django settings for horison project.
"""
import os
import sys
from pathlib import Path
from django.conf import settings
from django.conf.urls.static import static


# ============================================
# CONFIGURATION GIS PORTABLE (Linux Render et Windows local)
# ============================================

BASE_DIR = Path(__file__).resolve().parent.parent
os.environ.setdefault('PROJ_NETWORK', 'OFF')
os.environ.setdefault('PROJ_DEBUG', '0')

if os.name == 'nt':
    venv_path = os.getenv('VIRTUAL_ENV', r'D:\Horison\.venv')
    proj_candidates = [os.path.join(venv_path, 'Lib', 'site-packages', 'osgeo', 'data', 'proj'), os.path.join(venv_path, 'Lib', 'site-packages', 'pyproj', 'proj_dir', 'share', 'proj')]
    for proj_path in proj_candidates:
        if os.path.exists(os.path.join(proj_path, 'proj.db')):
            os.environ.setdefault('PROJ_LIB', proj_path)
            break
    osgeo_path = os.path.join(venv_path, 'Lib', 'site-packages', 'osgeo')
    gdal_dll = os.path.join(osgeo_path, 'gdal.dll')
    geos_dll = os.path.join(osgeo_path, 'geos_c.dll')
    if os.path.exists(gdal_dll): GDAL_LIBRARY_PATH = gdal_dll
    if os.path.exists(geos_dll): GEOS_LIBRARY_PATH = geos_dll
else:
    os.environ.setdefault('PROJ_LIB', '/usr/share/proj')
    os.environ.setdefault('GDAL_DATA', '/usr/share/gdal')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '*').split(',') if h.strip()]

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
        'NAME': 'Ecommune',
        'USER': 'postgres',
        'PASSWORD': '1234',
        'HOST': 'localhost',
        'PORT': '5432',
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
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')  # Votre email d'envoi
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')  # Votre mot de passe d'application Gmail
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# L'adresse email qui reçoit les alertes (Contrôlée par vous)
ALERT_RECIPIENT_EMAIL = os.getenv('ALERT_RECIPIENT_EMAIL', '') 

# Seuil NDVI pour déclencher une alerte (ex: < 0.35 = Stress hydrique sévère)
NDVI_ALERT_THRESHOLD = 0.35

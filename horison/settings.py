"""
Django settings for horison project.
"""
import os
import sys
from pathlib import Path
from django.conf import settings
from django.conf.urls.static import static


# ============================================
# CONFIGURATION GIS CRITIQUE (DOIT ÊTRE EN HAUT)
# ============================================

BASE_DIR = Path(__file__).resolve().parent.parent

# 1. DÉSACTIVER LES FONCTIONNALITÉS PROBABLES
os.environ['PROJ_NETWORK'] = 'OFF'
os.environ['PROJ_DEBUG'] = '0'

# 2. UTILISER PROJ DE VOTRE VENV (GDAL 3.11.4)
# Le chemin devrait être dans votre venv
venv_path = r"D:\Horison\.venv"

# Chercher proj.db dans le venv
proj_paths_to_try = [
    os.path.join(venv_path, "Lib", "site-packages", "osgeo", "data", "proj"),
    os.path.join(venv_path, "Lib", "site-packages", "osgeo", "proj"),
    os.path.join(venv_path, "Lib", "site-packages", "pyproj", "proj_dir", "share", "proj"),
    os.path.join(venv_path, "share", "proj"),
]

for proj_path in proj_paths_to_try:
    proj_db_path = os.path.join(proj_path, "proj.db")
    if os.path.exists(proj_db_path):
        os.environ['PROJ_LIB'] = proj_path
        print(f"✓ PROJ_LIB trouvé: {proj_path}")
        break
else:
    # Si non trouvé, désactiver la recherche automatique
    os.environ['PROJ_LIB'] = r'D:\Horison\.venv\Lib\site-packages\osgeo\data\proj'
    print(f"⚠ PROJ_LIB configuré par défaut")

# 3. CONFIGURER GDAL_DATA
gdal_data_paths = [
    os.path.join(venv_path, "Lib", "site-packages", "osgeo", "data", "gdal"),
    os.path.join(venv_path, "share", "gdal"),
]

for gdal_path in gdal_data_paths:
    if os.path.exists(gdal_path):
        os.environ['GDAL_DATA'] = gdal_path
        print(f"✓ GDAL_DATA trouvé: {gdal_path}")
        break

# 4. AJOUTER OSGEO AU PATH
osgeo_path = os.path.join(venv_path, "Lib", "site-packages", "osgeo")
if os.path.exists(osgeo_path):
    # Ajouter au début du PATH pour priorité
    os.environ["PATH"] = osgeo_path + ";" + os.environ["PATH"]
    print(f"✓ OSGeo ajouté au PATH: {osgeo_path}")

# 5. CONFIGURER LES CHEMINS DES LIBRAIRIES
GDAL_LIBRARY_PATH = os.path.join(osgeo_path, "gdal.dll")
GEOS_LIBRARY_PATH = os.path.join(osgeo_path, "geos_c.dll")

# Vérifier l'existence
if not os.path.exists(GDAL_LIBRARY_PATH):
    print(f"❌ GDAL library introuvable: {GDAL_LIBRARY_PATH}")
    # Chercher dans d'autres emplacements
    for root, dirs, files in os.walk(venv_path):
        for file in files:
            if file == "gdal.dll":
                GDAL_LIBRARY_PATH = os.path.join(root, file)
                print(f"✓ GDAL trouvé: {GDAL_LIBRARY_PATH}")
                break

if not os.path.exists(GEOS_LIBRARY_PATH):
    print(f"❌ GEOS library introuvable: {GEOS_LIBRARY_PATH}")
    for root, dirs, files in os.walk(venv_path):
        for file in files:
            if file == "geos_c.dll":
                GEOS_LIBRARY_PATH = os.path.join(root, file)
                print(f"✓ GEOS trouvé: {GEOS_LIBRARY_PATH}")
                break

print("=" * 50)
print("CONFIGURATION GIS:")
print(f"  GDAL_LIBRARY_PATH: {GDAL_LIBRARY_PATH}")
print(f"  GEOS_LIBRARY_PATH: {GEOS_LIBRARY_PATH}")
print(f"  PROJ_LIB: {os.environ.get('PROJ_LIB', 'Non défini')}")
print(f"  GDAL_DATA: {os.environ.get('GDAL_DATA', 'Non défini')}")
print("=" * 50)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-668s^s2k9$u3_zs8mps1+1dy5-)+%*dlmr3*yp-phgep2&!!vp'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

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
    'django.contrib.gis',
    'rest_framework',
    'geoportail',
    'corsheaders',  # <-- IMPORTANT: Doit être ici
    'agriculture'
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
 # --- CONFIGURATION EMAIL (Pour les alertes) ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'koutoumbogajules@gmail.com'  # Votre email d'envoi
EMAIL_HOST_PASSWORD = '9264Jules1998:'  # Votre mot de passe d'application Gmail
DEFAULT_FROM_EMAIL = 'koutoumbogajules@gmail.com'

# L'adresse email qui reçoit les alertes (Contrôlée par vous)
ALERT_RECIPIENT_EMAIL = 'koutoumbogabakota@gmail.com' 

# Seuil NDVI pour déclencher une alerte (ex: < 0.35 = Stress hydrique sévère)
NDVI_ALERT_THRESHOLD = 0.35
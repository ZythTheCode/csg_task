"""
Django settings for CSG Task Management and Monitoring System.
"""

from pathlib import Path
from decouple import config
import dj_database_url
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='csg-django-secret-key-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
AUTH_USER_MODEL = 'accounts.User'

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost,testserver,*').split(',')
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

INSTALLED_APPS = [
    'cloudinary_storage',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary',
    # Third-party
    'rest_framework',
    'crispy_forms',
    'crispy_bootstrap5',
    # Local apps
    'core',
    'accounts',
    'officers',
    'tasks',
    'monitoring',
    'reports',
    'notifications',
    'organizations',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'csg_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.notifications_processor',
                'organizations.context_processors.organization_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'csg_project.wsgi.application'

NEON_DB_URL = config('DATABASE_URL', default='')

# Database connection persistence strategy:
# - conn_max_age=600: Keep connections alive for 10 minutes to avoid TCP/SSL
#   handshake overhead on every request to Neon PostgreSQL.
# - conn_health_checks=True: Verify connection is usable before executing a query
#   on a reused connection (Django 4.1+). Stale connections are transparently replaced.
# - Connection limit: 1 persistent connection per gunicorn worker. Render free tier
#   runs 1-2 workers, so total connections = 1-2, well within Neon free-tier limit of 5.
if NEON_DB_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            NEON_DB_URL,
            ssl_require=not ('localhost' in NEON_DB_URL or '127.0.0.1' in NEON_DB_URL),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS'].update({
        'connect_timeout': 10,
        'keepalives_idle': 30,
    })
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudinary persistent media storage (configured for both production and local environments)
import cloudinary

CLOUDINARY_URL_ENV = config('CLOUDINARY_URL', default='').strip()
CLOUDINARY_CLOUD_NAME_ENV = config('CLOUDINARY_CLOUD_NAME', default='').strip()

if CLOUDINARY_URL_ENV or CLOUDINARY_CLOUD_NAME_ENV:
    c_name, a_key, a_secret = '', '', ''
    if CLOUDINARY_URL_ENV and 'cloudinary://' in CLOUDINARY_URL_ENV:
        try:
            creds, c_name = CLOUDINARY_URL_ENV.replace('cloudinary://', '').split('@')
            a_key, a_secret = creds.split(':')
        except Exception:
            pass
    else:
        c_name = CLOUDINARY_CLOUD_NAME_ENV
        a_key = config('CLOUDINARY_API_KEY', default='').strip()
        a_secret = config('CLOUDINARY_API_SECRET', default='').strip()

    if c_name and a_key and a_secret:
        os.environ['CLOUDINARY_URL'] = CLOUDINARY_URL_ENV
        CLOUDINARY_STORAGE = {
            'CLOUD_NAME': c_name,
            'API_KEY': a_key,
            'API_SECRET': a_secret,
            'PREFIX': '',
        }
        cloudinary.config(
            cloud_name=c_name,
            api_key=a_key,
            api_secret=a_secret,
            secure=True
        )

        RAW_MEDIA_ASSETS_STORAGE = 'core.storage.SmartRawMediaCloudinaryStorage'

        if not DEBUG:
            STORAGES = {
                "default": {
                    "BACKEND": "core.storage.SmartMediaCloudinaryStorage",
                },
                "staticfiles": {
                    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
                },
            }
        else:
            STORAGES = {
                "default": {
                    "BACKEND": "core.storage.SmartMediaCloudinaryStorage",
                },
                "staticfiles": {
                    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
                },
            }

# WhiteNoise: 1-year immutable caching headers for hashed static filenames
WHITENOISE_MAX_AGE = 31536000

# Cache configuration for performance (file-based survives process restarts)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / 'django_cache',
        'TIMEOUT': 300,
    }
}

# Use cached sessions to reduce DB hits per request
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

EMAIL_BACKEND       = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST          = config('EMAIL_HOST', default='smtp.gmail.com').strip()
EMAIL_PORT          = config('EMAIL_PORT', default=465, cast=int)
_use_tls            = config('EMAIL_USE_TLS', default=False, cast=bool)
_use_ssl            = config('EMAIL_USE_SSL', default=True, cast=bool)
EMAIL_USE_TLS       = _use_tls if EMAIL_PORT == 587 else False
EMAIL_USE_SSL       = _use_ssl if EMAIL_PORT == 465 else True
EMAIL_HOST_USER     = config('EMAIL_HOST_USER', default='').strip()
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='').strip().replace(' ', '')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL', default='').strip()
EMAIL_TIMEOUT       = 15

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',
        'user': '120/minute',
    },
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_UPLOAD_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.zip']

# Security Headers & Cookie Policies
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Structured Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} [{module}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
        },
        'csg.audit': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'csg.performance': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Performance monitoring thresholds
PERF_QUERY_COUNT_THRESHOLD = 15
PERF_REQUEST_DURATION_THRESHOLD_MS = 2000

# Django Debug Toolbar and performance logging (DEBUG only)
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']

    # Database query logging for slow queries (>100ms)
    LOGGING['loggers']['django.db.backends'] = {
        'handlers': ['console'],
        'level': 'WARNING',
        'propagate': False,
    }

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subfolder'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-prod-default-key-change-in-env')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG' if DEBUG else 'INFO')

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv(
        'ALLOWED_HOSTS',
        '*'
    ).split(',') if h.strip()
]

# Ensure Render, local, PythonAnywhere, and wildcard hosts are explicitly allowed
for default_host in ['*', 'sft-backend-apih.onrender.com', '.onrender.com', 'localhost', '127.0.0.1']:
    if default_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(default_host)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-Party Apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',

    # Domain Apps
    'Finance',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'src_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

import dj_database_url

WSGI_APPLICATION = 'src_backend.wsgi.application'

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

REDIS_URL = os.getenv('REDIS_URL')
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sft-local-cache",
        }
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

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'Finance.User'

# REST Framework Config
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
}

# SimpleJWT Config
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS Config
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:8080",
    "http://localhost:8888",
    "http://127.0.0.1:5173",
    "https://sfet.netlify.app",
    "https://sft-backend-apih.onrender.com",
    "https://sanjeevpratap99209920.pythonanywhere.com",
]
CORS_ALLOW_ALL_ORIGINS = DEBUG

from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-request-id",
]

# ─────────────────────────────────────────────────────────────────────────────
# STRUCTURED LOGGING — Production-Grade Observability
# ─────────────────────────────────────────────────────────────────────────────
# Log directory: BASE_DIR/logs/django.log (10MB × 5 rotating backups)
# Loggers:
#   'django'     → Django framework events (INFO and above)
#   'Finance'    → Domain app events (DEBUG in dev, INFO in prod)
#   'Finance.ai' → AI agent events (DEBUG in dev, WARNING in prod)
#   'config'     → Exception handler events (always WARNING+)
# ─────────────────────────────────────────────────────────────────────────────
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    # ── Formatters ────────────────────────────────────────────────────────────
    'formatters': {
        'verbose': {
            # Full context: level | timestamp | module | process | thread | message
            'format': '[{levelname}] {asctime} | {module} | pid:{process} | {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {asctime} | {message}',
            'style': '{',
            'datefmt': '%H:%M:%S',
        },
        'json_like': {
            # Structured format for log aggregators (Datadog, Logtail, etc.)
            'format': (
                '{{"level": "{levelname}", "time": "{asctime}", '
                '"module": "{module}", "message": "{message}"}}'
            ),
            'style': '{',
            'datefmt': '%Y-%m-%dT%H:%M:%S',
        },
    },

    # ── Handlers ──────────────────────────────────────────────────────────────
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': LOG_LEVEL,
        },
        'file_rotating': {
            # 10MB max per file, keep 5 backups = max 50MB log storage
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django.log'),
            'maxBytes': 10 * 1024 * 1024,   # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
            'level': LOG_LEVEL,
        },
    },

    # ── Loggers ───────────────────────────────────────────────────────────────
    'loggers': {
        'django': {
            'handlers': ['console', 'file_rotating'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file_rotating'],
            'level': 'WARNING',   # Only log 4xx/5xx request errors
            'propagate': False,
        },
        'Finance': {
            'handlers': ['console', 'file_rotating'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'Finance.ai': {
            # AI module can be very verbose — keep at WARNING in production
            'handlers': ['console', 'file_rotating'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'config': {
            # Exception handler logger — always capture warnings and above
            'handlers': ['console', 'file_rotating'],
            'level': 'WARNING',
            'propagate': False,
        },
    },

    # ── Root Logger ───────────────────────────────────────────────────────────
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

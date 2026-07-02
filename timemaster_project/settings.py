"""
Django settings for timemaster_project project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=None):
    value = os.environ.get(name)
    if value is None:
        return default or []
    return [item.strip() for item in value.replace(',', ' ').split() if item.strip()]


DATA_DIR = Path(os.environ.get('DATA_DIR', BASE_DIR))
LOG_DIR = Path(os.environ.get('LOG_DIR', BASE_DIR / 'logs'))
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', BASE_DIR / 'media'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-tr@p%q8j#9$k!z&*@x7v#1m9p&k@3r!9&5j8m#1k$5l&9n#2q',
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DEBUG', True)

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', ['*'])
for _host in ('localhost', '127.0.0.1'):
    if _host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_host)
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'timesheet',  # Our custom app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'timemaster_project.urls'

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
                'timesheet.context_processors.role_flags',
            ],
        },
    },
]

WSGI_APPLICATION = 'timemaster_project.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('SQLITE_PATH', DATA_DIR / 'db.sqlite3'),
    }
}

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.environ.get('TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Media files
MEDIA_URL = '/media/'
SERVE_MEDIA = env_bool('SERVE_MEDIA', DEBUG)

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Client timesheet imports can create entries as DRAFT or SUBMITTED.
CLIENT_TIMESHEET_IMPORT_STATUS = 'SUBMITTED'

# Login URL
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Session timeout: expire users after 8 hours of inactivity.
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', False)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', False)
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', False)

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)

EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# Accrual summary is sent as one consolidated email for all teams.
ACCRUAL_SUMMARY_TO_EMAILS = os.environ.get('ACCRUAL_SUMMARY_TO_EMAILS', '')
ACCRUAL_SUMMARY_CC_EMAILS = os.environ.get('ACCRUAL_SUMMARY_CC_EMAILS', '')


# ============ LOGGING CONFIGURATION ============
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'timemaster.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'errors.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'access_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'access.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'timesheet': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'timesheet.access': {
            'handlers': ['console', 'access_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'timesheet.email': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'timesheet.import': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import os as _os
for _directory in (DATA_DIR, LOG_DIR, MEDIA_ROOT):
    if not _os.path.exists(_directory):
        _os.makedirs(_directory)

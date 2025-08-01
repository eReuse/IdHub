"""
Django settings for trustchain_idhub project.

Generated by 'django-admin startproject' using Django 4.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""
import os

from ast import literal_eval
from dj_database_url import parse as db_url

from pathlib import Path
from django.contrib.messages import constants as messages
from decouple import config, Csv


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)
DEVELOPMENT = config('DEVELOPMENT', default=False, cast=bool)

DOMAIN = config("DOMAIN")
assert DOMAIN not in [None, ''], "DOMAIN var is MANDATORY"
# this var is very important, we print it
print("DOMAIN: " + DOMAIN)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default=DOMAIN, cast=Csv())
assert DOMAIN in ALLOWED_HOSTS, "DOMAIN is not ALLOWED_HOST"

CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default=f'https://{DOMAIN}', cast=Csv())

INIT_ADMIN_EMAIL = config("INIT_ADMIN_EMAIL", default='admin@example.org')
INIT_ADMIN_PASSWORD = config("INIT_ADMIN_PASSWORD", default='1234')

DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL', default='webmaster@localhost')

EMAIL_HOST = config('EMAIL_HOST', default='localhost')

EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')

EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

EMAIL_PORT = config('EMAIL_PORT', default=25, cast=int)

EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

EMAIL_FILE_PATH = config('EMAIL_FILE_PATH', default='/tmp/app-messages')

ADMINS = config('ADMINS', default='[]', cast=literal_eval)

MANAGERS = config('MANAGERS', default='[]', cast=literal_eval)

DPP = config("DPP", default='false', cast=bool)
API_DLT_URL = config("API_DLT_URL", default='')

if DPP:
    assert API_DLT_URL, "API_DLT_URL must be defined"

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'django_bootstrap5',
    'django_tables2',
    'idhub_auth',
    'oidc4vp',
    'idhub',
    'promotion',
    'webhook'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'trustchain_idhub.urls'

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

WSGI_APPLICATION = 'trustchain_idhub.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
if config('DB_TYPE', '') == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': config('DB_ENGINE', 'django.db.backends.postgresql'),
            'NAME': config('IDHUB_DB_NAME', 'idhub'),
            'USER': config('IDHUB_DB_USER', 'ereuse'),
            'PASSWORD': config('IDHUB_DB_PASSWORD', 'ereuse'),
            'HOST': config('IDHUB_DB_HOST', 'idhub-postgres'),
            'PORT': config('IDHUB_DB_PORT', '5432'),
        }
    }
# sqlite is fallback
else:
    DATABASES = {
        'default': config(
            'DATABASE_URL',
            default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'),
            cast=db_url)
    }


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

TIME_ZONE = config('TIME_ZONE', 'UTC')

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

STATIC_ROOT = config('STATIC_ROOT')
MEDIA_ROOT = config('MEDIA_ROOT', default=os.path.join(BASE_DIR, 'idhub/upload'))
FIXTURE_DIRS = (os.path.join(BASE_DIR, 'fixtures'),)
SCHEMAS_DIR = os.path.join(BASE_DIR, 'schemas')

STATICFILES_DIRS = [
    # following line was commented because caused a warning
    #   for a docker deployment (and it does not make sense)
    #os.path.join(BASE_DIR, 'static/'),
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = 'idhub:user_dashboard'
LOGOUT_REDIRECT_URL = 'idhub:login'

MESSAGE_TAGS = {
        messages.DEBUG: 'alert-secondary',
        messages.INFO: 'alert-info',
        messages.SUCCESS: 'alert-success',
        messages.WARNING: 'alert-warning',
        messages.ERROR: 'alert-danger',
 }

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]
# LANGUAGE_CODE="en"
# LANGUAGE_CODE="es"
LANGUAGE_CODE = config('LANGUAGE_CODE', "en")
gettext = lambda s: s
LANGUAGES = (
    ('de', gettext('German')),
    ('en', gettext('English')),
    ('ca', gettext('Catalan')),
    ('es', gettext('Spanish')),
)
USE_I18N = True
USE_L10N = True

AUTH_USER_MODEL = 'idhub_auth.User'

OIDC_REDIRECT = config('OIDC_REDIRECT', default=False, cast=bool)
ALLOW_CODE_URI = config(
    'ALLOW_CODE_URI',
    default=f"https://{DOMAIN}/oidc4vp/allow_code"
)

SUPPORTED_CREDENTIALS = config(
    'SUPPORTED_CREDENTIALS',
    default='[]',
    cast=literal_eval
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"level": "DEBUG", "class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    }
}

SYNC_ORG_DEV = config('SYNC_ORG_DEV', 'y')
OIDC_ORGS = config('OIDC_ORGS', '')
ENABLE_EMAIL = config('ENABLE_EMAIL', default=True, cast=bool)
CREATE_TEST_USERS = config('CREATE_TEST_USERS', default=False, cast=bool)
ENABLE_2FACTOR_AUTH = config('ENABLE_2FACTOR_AUTH', default=True, cast=bool)
ENABLE_DOMAIN_CHECKER = config('ENABLE_DOMAIN_CHECKER', default=True, cast=bool)
COMMIT = config('COMMIT', default='')
POLICY_PRIVACY = config(
    'POLICY_PRIVACY',
    default="https://laweb.pangea.org/politica-de-privacitat/"
)
POLICY_LEGAL = config(
    'POLICY_LEGAL',
    default="https://laweb.pangea.org/avis-legal/"
)
POLICY_COOKIES = config(
    'POLICY_COOKIES',
    default="https://laweb.pangea.org/politica-de-de-cookies-2/"
)
DEMO_CREATE_SCHEMAS = config('DEMO_CREATE_SCHEMAS', default=False, cast=bool)

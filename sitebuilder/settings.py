from pathlib import Path
import os
import secrets
import config
from urllib.parse import urlparse
from django.utils.translation import gettext_lazy as _
import sentry_sdk


BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_ROOT = 'static/'

SECRET_KEY = 'change_me_on_prod12783917'
import config as cfg

ALLOWED_HOSTS = ["*"]

DEBUG = cfg.DEBUG

USER_FILES_ROOT = f"{BASE_DIR}/users"

# Canonical host derived from config.SITE_URL
_parsed = urlparse(getattr(config, "SITE_URL", "http://localhost:8000"))
CANONICAL_SCHEME = _parsed.scheme or "http"
CANONICAL_NETLOC = _parsed.netloc or "localhost:8000"
CANONICAL_HOSTNAME = CANONICAL_NETLOC.split(":")[0]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "social_django",
    "django_celery_results",
    'sitebuilder',
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "sitebuilder.middleware.CanonicalHostMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
]

ROOT_URLCONF = "sitebuilder.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "core" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]

WSGI_APPLICATION = "sitebuilder.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": config.MARIADB["NAME"],
        "USER": config.MARIADB["USER"],
        "PASSWORD": config.MARIADB["PASSWORD"],
        "HOST": config.MARIADB["HOST"],
        "PORT": config.MARIADB["PORT"],
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            "charset": "utf8mb4",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
LANGUAGES = [
    ("ru", _("Russian")),
    ("en", _("English")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "core" / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = config.GOOGLE_OAUTH["CLIENT_ID"]
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = config.GOOGLE_OAUTH["CLIENT_SECRET"]
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ["email", "profile"]
SOCIAL_AUTH_LOGIN_ERROR_URL = "home"
SOCIAL_AUTH_REDIRECT_IS_HTTPS = CANONICAL_SCHEME == "https"

LOGIN_URL = "home"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"

# Helpful when hosting behind proxies; adjust if needed
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Sessions/cookies configuration to keep you logged in on the canonical host
SESSION_COOKIE_DOMAIN = CANONICAL_HOSTNAME
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = CANONICAL_SCHEME == "https"
CSRF_COOKIE_SECURE = CANONICAL_SCHEME == "https"

# CSRF trusted origins (useful in local dev and proxies)
CSRF_TRUSTED_ORIGINS = list({
    f"{CANONICAL_SCHEME}://{CANONICAL_NETLOC}",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "https://127.0.0.1:8000",
    "https://localhost:8000",
    cfg.SITE_URL,
})

CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "django-db"

CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1



CELERY_TASK_TIME_LIMIT = 60 * 10  # жесткий таймаут 10 минут
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 9

CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"

sentry_sdk.init(
    dsn="https://a955cf2914fdd9f9f43290ce1af65996@nsentry.itvx.biz/6",
)

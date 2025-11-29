"""Paramétrage Django principal pour le projet RAGCampus."""

import os
from pathlib import Path
import environ
import dj_database_url
# Chemins racine du projet (BASE_DIR = dossier webapp, ROOT_DIR = repository).
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

env = environ.Env(
    DEBUG=(bool, True),
)

ENV_FILE = ROOT_DIR / ".env"
if ENV_FILE.exists():
    environ.Env.read_env(ENV_FILE)

# Paramètres de démarrage rapide : à durcir avant tout déploiement.
# Guide Django : https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-bu_lio7r#uotj@vbrb^*qsq4s@%3yzbfnzixtj^8t_va#8cm@s",
)



# ⚠️ Ne laissez jamais DEBUG activé en production.
DEBUG = env.bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1","10.18.35.167"])

# Applications Django (cœur, dépendances tierces, app métier chatbot).
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "channels",
    "chatbot",
    "authentication",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "RAGCampus.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "RAGCampus.wsgi.application"
ASGI_APPLICATION = "RAGCampus.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Base de données par défaut : SQLite pour le développement local.
""""
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
"""

DATABASES={
    "default":dj_database_url.parse(os.environ.get("DATABASE_URL"))
}

# Validateurs de mots de passe recommandés pour les comptes utilisateurs.
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalisation (activer fr-fr ultérieurement si besoin côté UI).
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Emplacements des fichiers statiques/médias pour l'interface du chatbot.
STATIC_URL = "static/"
#STATICFILES_DIRS = [BASE_DIR / "static"]
#STATIC_ROOT = ROOT_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = ROOT_DIR / "media"

CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

MISTRAL_API_KEY = env("MISTRAL_API_KEY", default="")
FAISS_INDEX_PATH = env(
    "FAISS_INDEX_PATH", default=str(ROOT_DIR / "data" / "processed" / "faiss.index")
)

LOGIN_REDIRECT_URL= 'chatbot:chat'


# Identifiant auto par défaut pour les modèles.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

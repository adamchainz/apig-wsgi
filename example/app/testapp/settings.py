import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECRET_KEY = "not-really-secure"

DEBUG = os.environ.get("DEBUG", "0") == "1"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = []

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "testapp.urls"

TEMPLATES = []

WSGI_APPLICATION = "testapp.wsgi.application"

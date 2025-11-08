from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

# --- BASE DIR ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY ---
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-default-key")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

# --- AUTH ---
AUTH_USER_MODEL = "accounts.CustomUser"

# --- APPS ---
INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
]

# --- MIDDLEWARE ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Handles static on Railway/Render
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --- URL / WSGI ---
ROOT_URLCONF = "attendease.urls"
WSGI_APPLICATION = "attendease.wsgi.application"

# --- DATABASE (auto-detect Postgres or fallback to SQLite) ---
if "DATABASE_URL" in os.environ:
    DATABASES = {
        "default": dj_database_url.config(
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --- PASSWORD VALIDATORS ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- INTERNATIONALIZATION ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# --- STATIC & MEDIA ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Whitenoise for production static handling
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --- JAZZMIN CONFIG ---
JAZZMIN_SETTINGS = {
    "site_title": "AttendEase Admin",
    "site_header": "AttendEase Dashboard",
    "site_brand": "AttendEase",
    "welcome_sign": "Welcome to AttendEase Admin Portal",
    "site_logo": "logo.jpg",  # path in static/images/
    "copyright": "© 2025 AttendEase",
    "show_ui_builder": False,
    "topmenu_links": [
        {"name": "Home", "url": "/admin", "new_window": False},
        {"name": "Users", "url": "/admin/accounts/customuser/", "new_window": False},
        {"name": "Attendance", "url": "/admin/accounts/attendance/", "new_window": False},
        {"name": "Face Manage", "url": "/admin/accounts/facechangerequest/", "new_window": False},
        {"name": "Leave Request", "url": "/admin/accounts/leaverequest/", "new_window": False},
        {"name": "User Faces", "url": "/admin/accounts/userface", "new_window": False},
        {"name": "AttendEase Index Page", "url": "/", "new_window": True},
    ],
    "icons": {
        "accounts.Attendance": "fas fa-calendar-check",
        "accounts.FaceChangeRequest": "fas fa-user-edit",
        "accounts.LeaveRequest": "fas fa-plane-departure",
        "accounts.userface": "fas fa-id-card",
        "accounts.CustomUser": "fas fa-users",
        "auth.Group": "fas fa-users-cog",
    },
}

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "navbar": "navbar-dark bg-gradient-primary",
    "sidebar": "sidebar-dark-primary",
    "accent": "accent-purple",
    "navbar_fixed": True,
    "sidebar_fixed": True,
}

# --- DeepFace MODEL CACHE DIRECTORY ---
DEEPFACE_HOME = os.getenv(
    "DEEPFACE_HOME", str(BASE_DIR / "media" / "deepface_models" / ".deepface")
)
os.makedirs(DEEPFACE_HOME, exist_ok=True)
os.environ["DEEPFACE_HOME"] = DEEPFACE_HOME

# --- TEMPLATES ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "accounts" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- DEFAULT AUTO FIELD ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MONGO_URI = os.getenv("MONGO_URI", "")
    MONGO_DB = os.getenv("MONGO_DB", "promotion_review_management")
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY")
    AUTH_COOKIE_SECURE = APP_ENV == "production"
    AUTH_COOKIE_NAME = "__Host-auth" if AUTH_COOKIE_SECURE else "dev-auth"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = AUTH_COOKIE_SECURE
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 1024 * 1024
    MAX_FORM_MEMORY_SIZE = 1024 * 1024
    MAX_FORM_PARTS = 100
    AVATAR_STORAGE_DIR = os.getenv('AVATAR_STORAGE_DIR', os.path.join(os.path.dirname(__file__), 'instance', 'avatars'))
    FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5001"))
    CHECKOUT_ENABLED = os.getenv('CHECKOUT_ENABLED', 'false').lower() == 'true'
    JSON_AS_ASCII = False
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0


"""
Application configuration.
Reads sensitive values from environment variables (.env file) so credentials
are never hard-coded into the source.
"""
import os
import warnings
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

# Whether the app is running in production. Several protections below become
# strict/mandatory when this is true, so it must be set explicitly on any
# real deployment (e.g. FLASK_ENV=production in the platform's env vars).
IS_PRODUCTION = os.getenv("FLASK_ENV", "development").lower() == "production"


def _require_secret_key():
    key = os.getenv("SECRET_KEY")
    if key:
        return key
    if IS_PRODUCTION:
        # Never fall back to a guessable key in production: it would let an
        # attacker forge session cookies / CSRF tokens.
        raise RuntimeError(
            "SECRET_KEY environment variable must be set in production."
        )
    warnings.warn(
        "SECRET_KEY not set - using an insecure development-only key. "
        "Set SECRET_KEY in your .env before deploying.",
        RuntimeWarning,
    )
    return "dev-only-insecure-key-do-not-use-in-production"


class Config:
    SECRET_KEY = _require_secret_key()

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "exam_system")

    # URL-encode the password: special characters like @ : / ? # would
    # otherwise break the connection string's syntax.
    _DB_PASSWORD_ENCODED = quote_plus(DB_PASSWORD)

    # NOTE: TLS certificate verification for the DB connection is left at its
    # secure default here (previously it was explicitly disabled via
    # ?ssl_verify_cert=false, which allowed man-in-the-middle attacks against
    # the DB link). If your MySQL host needs a custom CA bundle, pass
    # ssl={"ca": "/path/to/ca.pem"} via SQLALCHEMY_ENGINE_OPTIONS instead of
    # disabling verification.
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{_DB_PASSWORD_ENCODED}@"
        f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEFAULT_EXAM_DURATION_MIN = 30

    # ---- Security hardening ----
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Requires HTTPS in production (Render/Railway/etc. terminate TLS in
    # front of the app, so this is safe to force on).
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = IS_PRODUCTION

    PERMANENT_SESSION_LIFETIME = 60 * 60 * 2  # 2 hours

    # Reject absurdly large request bodies (protects against some DoS /
    # upload-abuse vectors) - 2 MB is generous for this app's form posts.
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

    # ---- Email notifications (optional) ----
    # If MAIL_SERVER is unset, email_service.py skips sending instead of
    # raising, so the app works fine without SMTP configured.
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

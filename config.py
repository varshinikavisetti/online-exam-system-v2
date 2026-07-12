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

    # Some managed MySQL-compatible providers (TiDB Cloud Serverless,
    # PlanetScale, etc.) REQUIRE the connection itself to be TLS-encrypted
    # and reject plain connections outright ("Connections using insecure
    # transport are prohibited"). PyMySQL doesn't negotiate TLS unless told
    # to, so this is opt-in via DB_SSL rather than always-on: your local
    # MySQL almost certainly uses a self-signed cert that would fail
    # verification against the public CA bundle, breaking local dev.
    # Set DB_SSL=true in your deployment platform's environment variables
    # (Render/Railway/etc.) for providers that require it; leave it unset
    # locally. Uses ssl_verify_cert/ssl_verify_identity (PyMySQL's
    # documented kwargs, also what TiDB Cloud's own docs recommend) rather
    # than passing a raw ssl.SSLContext — the two are not equivalent in
    # every PyMySQL version and the raw-context form was silently not
    # forcing TLS in testing.
    DB_SSL = os.getenv("DB_SSL", "false").lower() == "true"
    if DB_SSL:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {
                "ssl_verify_cert": True,
                "ssl_verify_identity": True,
            }
        }

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

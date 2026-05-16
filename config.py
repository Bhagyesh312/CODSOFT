import os
import logging
from dotenv import load_dotenv

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('thinksprint')

# ── Constants (single source of truth) ────────────────────────────────────────
MIN_TIMER_SECONDS   = 5
MAX_TIMER_SECONDS   = 300
MIN_BONUS_POINTS    = 1
MAX_BONUS_POINTS    = 100
MAX_PENALTY         = 10.0
MIN_PENALTY         = 0.1
MIN_PASSWORD_LENGTH = 8
MAX_TITLE_LENGTH    = 200
MAX_DESC_LENGTH     = 1000
JOIN_CODE_LENGTH    = 6
MAX_UPLOAD_MB       = 5


class Config:
    # ── Core ──────────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///thinksprint.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Session / Cookie hardening ────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = 'Lax'
    # Only enforce Secure in production (HTTPS); dev uses HTTP
    SESSION_COOKIE_SECURE    = os.environ.get('FLASK_ENV') == 'production'
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7   # 7 days

    # ── Upload ────────────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    # Warn loudly if default secret key used in production
    @classmethod
    def init_app(cls, app):
        if app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production':
            logger.warning(
                'SECURITY WARNING: Using default SECRET_KEY in production. '
                'Set the SECRET_KEY environment variable immediately.'
            )


config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}

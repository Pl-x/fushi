from flask import Flask, render_template
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import text
from sqlalchemy.engine import URL
from .extensions import db, migrate, cors, limiter
import os
import logging
import re
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)


PSQL_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'password'),
    'db': os.getenv('POSTGRES_DB', 'payment_gateway')
}


_PLACEHOLDER_VALUES = {
    '', 'password', 'your-super-secret-key-change-this',
    'your-database-password', 'sk_test_your_paystack_secret_key',
    'sk_live_your_paystack_secret_key', 'change-me', 'secret', 'supersecretkey',
}


def _is_placeholder(value):
    """Return whether an environment value is absent or a known example value."""
    return not value or value.strip().lower() in _PLACEHOLDER_VALUES


def _allowed_origins():
    return [origin.strip().rstrip('/') for origin in os.getenv('ALLOWED_ORIGINS', '').split(',') if origin.strip()]


def _redis_url():
    """Support the common REDIS_URL name while preferring the limiter-specific name."""
    return os.getenv('RATELIMIT_STORAGE_URI') or os.getenv('REDIS_URL')


def _is_valid_redis_url(value):
    if _is_placeholder(value):
        return False
    try:
        parsed = urlparse(value)
        _ = parsed.port  # Validate a supplied port without requiring one.
        # A leading/trailing dot or two adjacent dots creates an invalid DNS label.
        return (
            parsed.scheme in {'redis', 'rediss'}
            and bool(parsed.hostname)
            and not parsed.hostname.startswith('.')
            and not parsed.hostname.endswith('.')
            and '..' not in parsed.hostname
        )
    except ValueError:
        return False


def _validate_production_environment():
    """Fail closed when deployment secrets or externally reachable settings are unsafe."""
    errors = []
    secret = os.getenv('SECRET_KEY')
    paystack_secret = os.getenv('PAYSTACK_SECRET_KEY')
    database_uri = os.getenv('SQLALCHEMY_DATABASE_URI', '')
    redis_url = _redis_url()
    origins = _allowed_origins()

    if _is_placeholder(secret) or len(secret) < 32:
        errors.append('SECRET_KEY must be a non-placeholder value of at least 32 characters')
    if _is_placeholder(paystack_secret) or not paystack_secret.startswith('sk_live_'):
        errors.append('PAYSTACK_SECRET_KEY must be a non-placeholder sk_live_ key')
    components_valid = all(not _is_placeholder(PSQL_CONFIG[name]) for name in ('host', 'user', 'password', 'db'))
    uri_valid = database_uri.startswith(('postgresql://', 'postgresql+psycopg2://')) and 'placeholder' not in database_uri.lower()
    if not (components_valid or uri_valid):
        errors.append('PostgreSQL credentials or SQLALCHEMY_DATABASE_URI must be configured')
    if not _is_valid_redis_url(redis_url):
        errors.append('RATELIMIT_STORAGE_URI or REDIS_URL must be a valid redis:// or rediss:// URL')
    if not origins or any(not origin.startswith('https://') for origin in origins):
        errors.append('ALLOWED_ORIGINS must contain one or more HTTPS origins')
    if errors:
        raise RuntimeError('Production configuration is invalid: ' + '; '.join(errors))


def create_app():
    app = Flask(__name__)
    app_environment = os.getenv('APP_ENV', 'development').lower()
    if app_environment not in {'development', 'testing', 'production'}:
        raise RuntimeError('APP_ENV must be development, testing, or production')
    if app_environment == 'production':
        _validate_production_environment()

    # Configure the app with PostgreSQL settings
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretkey')
    app.config['TESTING'] = os.getenv('TESTING', '').lower() == 'true'
    app.config['JWT_EXPIRATION_DELTA'] = int(os.getenv('JWT_EXPIRATION_DELTA', 3600))  # Default to 1 hour
    # URL.create escapes credentials correctly. Passwords supplied by managed
    # PostgreSQL providers commonly contain @, :, /, or other URL characters.
    default_database_uri = URL.create(
        'postgresql',
        username=PSQL_CONFIG['user'],
        password=PSQL_CONFIG['password'],
        host=PSQL_CONFIG['host'],
        port=int(PSQL_CONFIG['port']),
        database=PSQL_CONFIG['db'],
    )
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'SQLALCHEMY_DATABASE_URI', default_database_uri
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['AUTO_CREATE_SCHEMA'] = os.getenv(
        'AUTO_CREATE_SCHEMA', os.getenv('FLASK_DEBUG', 'false')
    ).lower() == 'true'
    if app_environment == 'production':
        app.config['AUTO_CREATE_SCHEMA'] = False
    app.config['SESSION_COOKIE_SECURE'] = app_environment == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
    if app.config['TESTING']:
        app.config['RATELIMIT_STORAGE_URI'] = 'memory://'
        app.config['RATELIMIT_ENABLED'] = False
    else:
        app.config['RATELIMIT_STORAGE_URI'] = _redis_url() or 'redis://localhost:6379/0'

    if os.getenv('TRUST_PROXY_HEADERS', '').lower() == 'true':
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={
        r"/api/v1/*": {
            "origins": _allowed_origins() if app_environment == 'production' else "*",
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    from .routes.paystack import paystack_bp
    from .routes.AAA import aaa_bp
    from .routes.B2C import b2c_bp
    from .routes.C2B import c2b_bp
    from .routes.portal import portal_bp
    
    app.register_blueprint(paystack_bp, url_prefix='/api/v1/paystack')
    app.register_blueprint(aaa_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(b2c_bp, url_prefix='/api/v1/b2c')
    app.register_blueprint(c2b_bp, url_prefix='/api/v1/c2b')
    app.register_blueprint(portal_bp, url_prefix='/api/v1/portal')

    # Set up rate limiting
    limiter.init_app(app)
    app.config['RATELIMIT_DEFAULT'] = "200 per day; 50 per hour"

    @app.get('/')
    def index():
        return render_template('checkout.html')

    @app.get('/health')
    @limiter.exempt
    def health():
        return {"status": "healthy"}, 200

    @app.get('/welcome')
    def welcome():
        return render_template('checkout.html')

    @app.get('/signin')
    def signin_page():
        return render_template('signin.html')

    @app.get('/signup')
    def signup_page():
        return render_template('signup.html')

    @app.get('/dashboard')
    def dashboard():
        return render_template('dashboard.html')

    @app.get('/hotels')
    def hotels():
        return render_template('hotels.html')

    @app.get('/review')
    def review():
        return render_template('review_modal.html')

    @app.get('/receipt')
    def receipt():
        return render_template('receipt.html')

    @app.get('/profile')
    def profile():
        return render_template('profile.html')

    @app.get('/reviews')
    def reviews():
        return render_template('reviews.html')

    @app.get('/admin')
    def admin():
        return render_template('admin_login.html')

    @app.get('/admin/login')
    def admin_login_page():
        return render_template('admin_login.html')

    @app.get('/admin/portal')
    def admin_portal():
        return render_template('admin.html')

    @app.get('/admin/payouts')
    def admin_payouts():
        return render_template('admin_payouts.html')

    @app.get('/deposit')
    def deposit():
        return render_template('deposit.html')

    @app.after_request
    def add_theme_assets(response):
        """Attach compiled styling, theme controls, and browser security headers."""
        if response.mimetype == 'text/html':
            document = response.get_data(as_text=True)
            # Do not ship the Tailwind CDN compiler in production responses.
            document = re.sub(
                r'<script[^>]+src=["\']https?://cdn\.tailwindcss\.com[^>]*></script>',
                '', document, flags=re.IGNORECASE,
            )
            if '</head>' in document and '/static/theme.js' not in document:
                assets = (
                    '<link rel="stylesheet" href="/static/css/app.css">'
                    '<link rel="stylesheet" href="/static/theme.css">'
                    '<script src="/static/theme.js"></script>'
                )
                response.set_data(document.replace('</head>', f'{assets}</head>', 1))
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        if app_environment == 'production':
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

    # This project is currently in development. Keep the database schema in
    # sync regardless of whether it is started with Flask or Gunicorn.
    if app.config['AUTO_CREATE_SCHEMA']:
        with app.app_context():
            # Gunicorn can boot several workers at once. PostgreSQL's
            # checkfirst is not a cross-process lock, so serialize schema
            # creation to avoid concurrent CREATE TABLE races.
            if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql'):
                with db.engine.begin() as connection:
                    connection.execute(text('SELECT pg_advisory_lock(8142026)'))
                    try:
                        db.create_all()
                        # create_all does not change an existing column. This
                        # development-only compatibility step fixes databases
                        # created when Hotel.image_url was VARCHAR(500).
                        connection.execute(text(
                            'ALTER TABLE IF EXISTS hotels '
                            'ALTER COLUMN image_url TYPE TEXT'
                        ))
                        connection.execute(text(
                            'ALTER TABLE IF EXISTS users '
                            'ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE'
                        ))
                        connection.execute(text(
                            'ALTER TABLE IF EXISTS payout_requests '
                            'ADD COLUMN IF NOT EXISTS transfer_id INTEGER REFERENCES transfers(id)'
                        ))
                        connection.execute(text(
                            'CREATE UNIQUE INDEX IF NOT EXISTS '
                            'ix_payout_requests_transfer_id ON payout_requests (transfer_id) '
                            'WHERE transfer_id IS NOT NULL'
                        ))
                        connection.execute(text(
                            'ALTER TABLE IF EXISTS hotels ADD COLUMN IF NOT EXISTS '
                            'review_reward_cents INTEGER NOT NULL DEFAULT 102100'
                        ))
                    finally:
                        connection.execute(text('SELECT pg_advisory_unlock(8142026)'))
            else:
                db.create_all()
        logging.info("Database schema ensured (AUTO_CREATE_SCHEMA=true).")

    logging.info("Flask application created and configured.")
    
    return app

from flask import Flask, render_template
from sqlalchemy import text
from .extensions import db, migrate, cors, limiter
import os
import logging

logging.basicConfig(level=logging.INFO)


PSQL_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'password'),
    'db': os.getenv('POSTGRES_DB', 'payment_gateway')
}


def create_app():
    app = Flask(__name__)
    
    # Configure the app with PostgreSQL settings
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretkey')
    app.config['TESTING'] = os.getenv('TESTING', '').lower() == 'true'
    app.config['JWT_EXPIRATION_DELTA'] = int(os.getenv('JWT_EXPIRATION_DELTA', 3600))  # Default to 1 hour
    default_database_uri = (
        f"postgresql://{PSQL_CONFIG['user']}:{PSQL_CONFIG['password']}"
        f"@{PSQL_CONFIG['host']}:{PSQL_CONFIG['port']}/{PSQL_CONFIG['db']}"
    )
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'SQLALCHEMY_DATABASE_URI', default_database_uri
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['AUTO_CREATE_SCHEMA'] = os.getenv(
        'AUTO_CREATE_SCHEMA', os.getenv('FLASK_DEBUG', 'false')
    ).lower() == 'true'
    if app.config['TESTING']:
        app.config['RATELIMIT_STORAGE_URI'] = 'memory://'
        app.config['RATELIMIT_ENABLED'] = False
    else:
        app.config['RATELIMIT_STORAGE_URI'] = os.getenv(
            'RATELIMIT_STORAGE_URI', 'redis://localhost:6379'
        )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={
        r"/api/v1/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    from .routes.paystack import paystack_bp
    from .routes.AAA import aaa_bp
    from .routes.B2C import b2c_bp
    from .routes.C2B import c2b_bp
    
    app.register_blueprint(paystack_bp, url_prefix='/api/v1/paystack')
    app.register_blueprint(aaa_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(b2c_bp, url_prefix='/api/v1/b2c')
    app.register_blueprint(c2b_bp, url_prefix='/api/v1/c2b')

    # Set up rate limiting
    limiter.init_app(app)
    app.config['RATELIMIT_DEFAULT'] = "200 per day; 50 per hour"

    @app.get('/')
    def index():
        return {"status": "success", "message": "Payment Gateway API is running", "version": "1.0.0"}, 200

    @app.get('/health')
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
                    finally:
                        connection.execute(text('SELECT pg_advisory_unlock(8142026)'))
            else:
                db.create_all()
        logging.info("Database schema ensured (AUTO_CREATE_SCHEMA=true).")

    logging.info("Flask application created and configured.")
    
    return app

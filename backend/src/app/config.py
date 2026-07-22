from flask import Flask
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
    app.config['JWT_EXPIRATION_DELTA'] = int(os.getenv('JWT_EXPIRATION_DELTA', 3600))  # Default to 1 hour
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{PSQL_CONFIG['user']}:{PSQL_CONFIG['password']}@{PSQL_CONFIG['host']}:{PSQL_CONFIG['port']}/{PSQL_CONFIG['db']}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

    logging.info("Flask application created and configured.")
    
    return app

"""
Application entry point
Run this file to start the Flask development server
"""
import os
from src.app.main import app
from src.app.extensions import db

if __name__ == '__main__':
    # Schema changes belong to Alembic migrations.  Keep this development
    # convenience behind the same explicit opt-in as the application factory.
    if app.config['AUTO_CREATE_SCHEMA']:
        with app.app_context():
            db.create_all()
            print("Database schema ensured (development only).")
    
    # Get port from environment or default to 5000
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"Starting Flask application on port {port}")
    print(f"Debug mode: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )

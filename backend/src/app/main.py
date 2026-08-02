"""
Main Flask application entry point
"""
from .config import create_app
from .extensions import db

app = create_app()

if __name__ == '__main__':
    if app.config['AUTO_CREATE_SCHEMA']:
        with app.app_context():
            db.create_all()
    app.run(debug=True)

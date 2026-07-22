"""
Main Flask application entry point
"""
from .config import create_app
from .extensions import db

app = create_app()

@app.route('/')
def index():
    """Health check endpoint"""
    return {
        "status": "success",
        "message": "Payment Gateway API is running",
        "version": "1.0.0"
    }, 200

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "healthy"}, 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

# Load environment variables from .env file
load_dotenv()
# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()   

limiter = Limiter(
    get_remote_address,
    default_limits=["20 per minute", "2 per second"],
    strategy="fixed-window"
)

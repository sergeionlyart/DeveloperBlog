import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_misaka import Misaka
from flask_caching import Cache

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Set up base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
md = Misaka(fenced_code=True, highlight=True, autolink=True, escape=True)
cache = Cache()
login_manager = LoginManager()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure the database (SQLite for simplicity)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///blog.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure caching
app.config["CACHE_TYPE"] = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300

# Initialize extensions with app
db.init_app(app)
md.init_app(app)
cache.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import routes after app is created to avoid circular imports
with app.app_context():
    # Import models and routes
    import models
    import routes

    # Create database tables if they don't exist
    db.create_all()

    # Initialize admin user if it doesn't exist
    from models import User
    from werkzeug.security import generate_password_hash
    
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin_user = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("admin"),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        logging.info("Admin user created")

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

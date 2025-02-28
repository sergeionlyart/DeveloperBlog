import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash

logging.basicConfig(level=logging.DEBUG)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "adminpassword"
ADMIN_EMAIL = "admin@example.com"

logging.info(f"Default admin credentials: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")

# Инициализация расширений
db = SQLAlchemy()
cache = Cache()
login_manager = LoginManager()
csrf = CSRFProtect()

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL",
                                                       "sqlite:///blog.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 10,
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["CACHE_TYPE"] = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300

# Инициализация расширений
db.init_app(app)
cache.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
csrf.init_app(app)  # CSRF включён обратно


@app.teardown_appcontext
def shutdown_session(exception=None):
    if exception:
        db.session.rollback()
    db.session.remove()


@app.after_request
def after_request(response):
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error("Database commit error: %s", e)
    finally:
        db.session.remove()
    return response


with app.app_context():
    try:
        import models
        import routes
        db.create_all()

        from models import User
        admin = User.query.filter_by(username=ADMIN_USERNAME).first()
        if not admin:
            admin_user = User(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                password_hash=generate_password_hash(ADMIN_PASSWORD),
                is_admin=True)
            db.session.add(admin_user)
            db.session.commit()
            logging.info(
                f"Admin user '{ADMIN_USERNAME}' created successfully.")
    except Exception as e:
        db.session.rollback()
        logging.error("Error during application initialization: %s", e)


@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))


if __name__ == "__main__":
    app.run(debug=True)

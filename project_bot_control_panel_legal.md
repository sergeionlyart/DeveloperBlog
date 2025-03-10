# Project Structure
```
```

# Source Code

## app.py
```python
# app.py
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_misaka import Misaka
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

# Статичные данные администратора
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "adminpassword"  # В реальном приложении используйте более сложный пароль
ADMIN_EMAIL = "admin@example.com"

logging.info(f"Default admin credentials: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")

# Инициализация расширений
db = SQLAlchemy(
)  # Используем стандартный способ, без кастомного базового класса
md = Misaka(fenced_code=True, highlight=True, autolink=True, escape=True)
cache = Cache()
login_manager = LoginManager()
csrf = CSRFProtect()

# Создание приложения
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Конфигурация базы данных (SQLite для простоты)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL",
                                                       "sqlite:///blog.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Конфигурация кэширования
app.config["CACHE_TYPE"] = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300

# Инициализация расширений с приложением
db.init_app(app)
md.init_app(app)
cache.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
csrf.init_app(app)  # Инициализация CSRF защиты


# Обработчик завершения контекста для очистки сессии
@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()


# Импорт маршрутов и моделей после создания приложения для избежания циклических импортов
with app.app_context():
    try:
        import models
        import routes

        # Создание таблиц в базе данных, если они ещё не существуют
        db.create_all()

        # Инициализация администратора, если он отсутствует
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
                f"Admin user '{ADMIN_USERNAME}' created with stated password")
    except Exception as e:
        db.session.rollback()
        logging.error("Error during application initialization: %s", e)


@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))


if __name__ == "__main__":
    app.run(debug=True)
```

## create_admin.py
```python
from app import app, db
from models import User
from werkzeug.security import generate_password_hash
import logging

logging.basicConfig(level=logging.INFO)

def create_admin_user(username, email, password):
    """Create an admin user for the blog."""
    try:
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            if existing_user.username == username:
                logging.info(f"User with username '{username}' already exists.")
            if existing_user.email == email:
                logging.info(f"User with email '{email}' already exists.")
            return False
            
        # Create new user
        user = User(
            username=username, 
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=True
        )
        
        db.session.add(user)
        db.session.commit()
        logging.info(f"Admin user '{username}' created successfully.")
        return True
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating admin user: {str(e)}")
        return False

if __name__ == "__main__":
    # Run with app context
    with app.app_context():
        # Default admin credentials - for testing only
        username = "admin"
        email = "admin@example.com"
        password = "adminpassword"
        
        print("Create Admin User")
        print("-----------------")
        print(f"Using credentials: username='{username}', email='{email}', password='{password}'")
        
        # Create the admin user
        if create_admin_user(username, email, password):
            print(f"\nAdmin user '{username}' created successfully!")
            print(f"You can now login at /login with these credentials.")
        else:
            print("\nFailed to create admin user or user already exists.")```

## main.py
```python
import os
import signal
import logging
import threading
from app import app

# Флаг для отслеживания состояния логирования
# Предотвращает рекурсивные вызовы при обработке сигналов
_logging_in_progress = threading.Lock()

# Настройка безопасного логирования для предотвращения реентрантных вызовов
def safe_log(level, message):
    """Логирование с блокировкой для предотвращения проблем с реентрантностью"""
    if _logging_in_progress.acquire(blocking=False):
        try:
            if level == 'debug':
                logging.debug(message)
            elif level == 'info':
                logging.info(message)
            elif level == 'warning':
                logging.warning(message)
            elif level == 'error':
                logging.error(message)
            elif level == 'critical':
                logging.critical(message)
        finally:
            _logging_in_progress.release()

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Улучшенный обработчик сигналов для предотвращения зависаний
def handle_signal(signum, frame):
    """Усовершенствованный обработчик сигналов
    
    Важно: Используем safe_log чтобы избежать реентрантных вызовов и зависаний.
    Полностью игнорируем SIGWINCH, который вызывает большинство проблем.
    """
    # Полностью игнорируем SIGWINCH, чтобы предотвратить каскадное логирование
    if signum == signal.SIGWINCH:
        return
        
    signal_names = {
        signal.SIGTERM: "SIGTERM (termination)",
        signal.SIGINT: "SIGINT (interrupt)",
        signal.SIGHUP: "SIGHUP (hangup)"
    }
    
    signal_name = signal_names.get(signum, f"Signal {signum}")
    
    # Используем безопасное логирование для предотвращения зависаний
    safe_log('info', f"Received {signal_name}, handling gracefully")
    
    # Для сигналов завершения (TERM, INT, HUP) делаем специальную обработку
    if signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        # Очищаем кэш при аккуратном завершении приложения
        try:
            from app import cache
            cache.clear()
            safe_log('info', "Cache cleared during shutdown")
        except Exception:
            pass

# Регистрируем обработчики сигналов
for sig in (signal.SIGWINCH, signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
    try:
        signal.signal(sig, handle_signal)
        safe_log('info', f"Successfully registered handler for signal {sig}")
    except (AttributeError, ValueError) as e:
        safe_log('warning', f"Could not register handler for signal {sig}: {e}")

# Логируем информацию о запуске
safe_log('info', "Application initialization completed")

if __name__ == "__main__":
    safe_log('info', "Starting Flask development server")
    app.run(host="0.0.0.0", port=5000, debug=True)
```

## migrate_db.py
```python
from app import app, db
import logging
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)

def migrate_database():
    """Применяет изменения схемы базы данных."""
    try:
        with app.app_context():
            # Создаем все таблицы по обновленным моделям
            db.create_all()
            logging.info("Database tables created/verified.")
            
            # Выполняем SQL-запросы для обновления существующих полей по очереди
            # 1. Изменение meta_description на TEXT если он существует как VARCHAR
            check_sql = text("""
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'article' 
                AND column_name = 'meta_description'
                AND data_type = 'character varying'
            """)
            
            result = db.session.execute(check_sql).fetchone()
            if result:
                logging.info("Changing meta_description column type to TEXT...")
                alter_sql = text("ALTER TABLE article ALTER COLUMN meta_description TYPE TEXT")
                db.session.execute(alter_sql)
                logging.info("meta_description column type changed.")
            
            # 2. Изменение meta_title на VARCHAR(200) если он существует и короче
            check_sql = text("""
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'article' 
                AND column_name = 'meta_title'
                AND character_maximum_length < 200
            """)
            
            result = db.session.execute(check_sql).fetchone()
            if result:
                logging.info("Changing meta_title column length to 200...")
                alter_sql = text("ALTER TABLE article ALTER COLUMN meta_title TYPE VARCHAR(200)")
                db.session.execute(alter_sql)
                logging.info("meta_title column length changed.")
            
            # 3. Изменение meta_keywords на VARCHAR(200) если он существует и короче
            check_sql = text("""
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'article' 
                AND column_name = 'meta_keywords'
                AND character_maximum_length < 200
            """)
            
            result = db.session.execute(check_sql).fetchone()
            if result:
                logging.info("Changing meta_keywords column length to 200...")
                alter_sql = text("ALTER TABLE article ALTER COLUMN meta_keywords TYPE VARCHAR(200)")
                db.session.execute(alter_sql)
                logging.info("meta_keywords column length changed.")
            
            # Фиксируем изменения
            db.session.commit()
            logging.info("All database schema changes applied successfully.")
            
    except Exception as e:
        logging.error(f"Error during database migration: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("Database Migration")
    print("-----------------")
    
    success = migrate_database()
    
    if success:
        print("\nDatabase migration completed successfully!")
    else:
        print("\nDatabase migration failed. Check the error logs.")```

## models.py
```python
from datetime import datetime
from app import db
from flask_login import UserMixin
from slugify import slugify

# Association table for many-to-many relationships
article_tags = db.Table(
    'article_tags',
    db.Column('article_id',
              db.Integer,
              db.ForeignKey('article.id'),
              primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True))


class User(UserMixin, db.Model):
    __tablename__ = 'user'  # Добавлено явное задание имени таблицы
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    articles = db.relationship('Article', backref='author', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    __tablename__ = 'category'  # Добавлено явное задание имени таблицы
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text)
    articles = db.relationship('Article', backref='category', lazy='dynamic')

    def __init__(self, *args, **kwargs):
        if 'slug' not in kwargs:
            kwargs['slug'] = slugify(kwargs.get('name', ''))
        super(Category, self).__init__(*args, **kwargs)

    def __repr__(self):
        return f'<Category {self.name}>'


class Tag(db.Model):
    __tablename__ = 'tag'  # Добавлено явное задание имени таблицы
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)

    def __init__(self, *args, **kwargs):
        if 'slug' not in kwargs:
            kwargs['slug'] = slugify(kwargs.get('name', ''))
        super(Tag, self).__init__(*args, **kwargs)

    def __repr__(self):
        return f'<Tag {self.name}>'


class Article(db.Model):
    __tablename__ = 'article'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,
                           default=datetime.utcnow,
                           onupdate=datetime.utcnow)
    published = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    tags = db.relationship('Tag',
                           secondary=article_tags,
                           backref=db.backref('articles', lazy='dynamic'))
    meta_title = db.Column(db.String(200))
    meta_description = db.Column(
        db.Text)  # Используем Text для поддержки длинных описаний
    meta_keywords = db.Column(db.String(200))

    def __init__(self, *args, **kwargs):
        if 'slug' not in kwargs:
            kwargs['slug'] = slugify(kwargs.get('title', ''))
        super(Article, self).__init__(*args, **kwargs)

    def __repr__(self):
        return f'<Article {self.title}>'
```

## reset_admin.py
```python
from app import app, db, ADMIN_USERNAME, ADMIN_PASSWORD
from models import User
from werkzeug.security import generate_password_hash
import logging

logging.basicConfig(level=logging.INFO)

def reset_admin_password():
    """Сбрасывает пароль администратора на значение по умолчанию."""
    try:
        with app.app_context():
            # Находим пользователя admin
            admin = User.query.filter_by(username=ADMIN_USERNAME).first()
            if not admin:
                logging.error(f"Пользователь {ADMIN_USERNAME} не найден")
                return False
                
            # Обновляем хеш пароля
            admin.password_hash = generate_password_hash(ADMIN_PASSWORD)
            db.session.commit()
            
            # Выводим новый хеш для отладки
            logging.info(f"Пароль администратора сброшен на значение по умолчанию")
            logging.info(f"Новый хеш пароля: {admin.password_hash}")
            
            return True
            
    except Exception as e:
        logging.error(f"Ошибка при сбросе пароля: {str(e)}")
        return False

if __name__ == "__main__":
    print("Сброс пароля администратора")
    print("--------------------------")
    
    if reset_admin_password():
        print(f"\nПароль администратора успешно сброшен!")
        print(f"Теперь вы можете войти с учетными данными:")
        print(f"Логин: {ADMIN_USERNAME}")
        print(f"Пароль: {ADMIN_PASSWORD}")
    else:
        print("\nНе удалось сбросить пароль администратора.")```

## routes.py
```python
import os
import re
import logging
import time
import sys
import traceback
from datetime import datetime
from functools import wraps

from flask import render_template, request, redirect, url_for, flash, abort, jsonify, make_response, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import desc
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, HiddenField
from wtforms.validators import DataRequired

from app import app, db, cache
from models import User, Category, Tag, Article
from utils import generate_sitemap

# Настройка логирования с форматированием для отслеживания времени и контекста
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout)
logger = logging.getLogger(__name__)


# Декоратор для отслеживания времени выполнения функций
def log_execution_time(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"START: {func.__name__}")
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            logger.debug(
                f"END: {func.__name__} - Execution time: {execution_time:.2f} sec"
            )
            return result
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.error(
                f"ERROR in {func.__name__} - Execution time: {execution_time:.2f} sec"
            )
            logger.error(f"Exception: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    return wrapper


# Декоратор для маршрутов, доступных только администраторам
def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


# Public routes
@app.route('/')
@cache.cached(timeout=60)
def index():
    page = request.args.get('page', 1, type=int)
    articles = Article.query.filter_by(published=True).order_by(
        desc(Article.created_at)).paginate(page=page, per_page=5)
    categories = Category.query.all()
    return render_template('index.html',
                           articles=articles,
                           categories=categories,
                           title="Developer Blog")


@app.route('/blog/<slug>')
@cache.cached(timeout=60)
def article(slug):
    article = Article.query.filter_by(slug=slug, published=True).first_or_404()

    # Создание хлебных крошек
    breadcrumbs = [('Home', url_for('index'))]
    if article.category:
        breadcrumbs.append((article.category.name,
                            url_for('category', slug=article.category.slug)))
    breadcrumbs.append((article.title, ''))

    return render_template('article.html',
                           article=article,
                           Article=Article,
                           breadcrumbs=breadcrumbs,
                           title=article.meta_title or article.title,
                           description=article.meta_description
                           or article.summary)


@app.route('/category/<slug>')
@cache.cached(timeout=60)
def category(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    articles = Article.query.filter_by(
        category=category,
        published=True).order_by(desc(Article.created_at)).paginate(page=page,
                                                                    per_page=5)

    # Создание хлебных крошек
    breadcrumbs = [('Home', url_for('index')),
                   (f"Category: {category.name}", '')]

    return render_template('category.html',
                           category=category,
                           articles=articles,
                           breadcrumbs=breadcrumbs,
                           title=f"Category: {category.name}",
                           description=category.description
                           or f"Articles in the {category.name} category.")


@app.route('/tag/<slug>')
@cache.cached(timeout=60)
def tag(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    articles = tag.articles.filter_by(published=True).order_by(
        desc(Article.created_at)).paginate(page=page, per_page=5)

    # Создание хлебных крошек
    breadcrumbs = [('Home', url_for('index')), (f"Tag: {tag.name}", '')]

    return render_template('tag.html',
                           tag=tag,
                           articles=articles,
                           breadcrumbs=breadcrumbs,
                           title=f"Tag: {tag.name}",
                           description=f"Articles tagged with {tag.name}.")


@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    articles = Article.query.filter(
        Article.published == True,
        (Article.title.ilike(f'%{query}%')
         | Article.content.ilike(f'%{query}%')
         | Article.summary.ilike(f'%{query}%'))).order_by(
             desc(Article.created_at)).paginate(page=page, per_page=5)

    categories = Category.query.all()

    # Создание хлебных крошек
    breadcrumbs = [('Home', url_for('index')), (f"Search: {query}", '')]

    return render_template(
        'index.html',
        articles=articles,
        categories=categories,
        search_query=query,
        breadcrumbs=breadcrumbs,
        title=f"Search: {query}",
        description=
        f"Search results for '{query}' - find relevant developer articles and tutorials."
    )


# Admin routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    from app import ADMIN_USERNAME, ADMIN_PASSWORD
    from flask_wtf.csrf import validate_csrf
    from wtforms import ValidationError

    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        # Проверка CSRF токена
        try:
            validate_csrf(request.form.get('csrf_token'))
        except Exception:
            flash('CSRF token validation failed. Please try again.', 'danger')
            return render_template('admin/login.html', title="Login")

        username = request.form.get('username')
        password = request.form.get('password')

        # Аутентификация пользователя
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('admin/login.html', title="Login")


@app.route('/logout')
@login_required
def logout():
    logout_user()  # Завершаем сессию пользователя
    session.clear()  # Очищаем данные сессии
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    logger.debug("Entering admin_dashboard route")
    try:
        articles_count = Article.query.count()
        logger.debug(f"articles_count: {articles_count}")
        published_count = Article.query.filter_by(published=True).count()
        logger.debug(f"published_count: {published_count}")
        draft_count = articles_count - published_count
        categories_count = Category.query.count()
        logger.debug(f"categories_count: {categories_count}")
        tags_count = Tag.query.count()
        logger.debug(f"tags_count: {tags_count}")
        recent_articles = Article.query.order_by(desc(
            Article.created_at)).limit(5).all()
        logger.debug(f"recent_articles count: {len(recent_articles)}")
    except Exception as ex:
        logger.error(f"Error in admin_dashboard queries: {ex}")
        raise

    return render_template('admin/dashboard.html',
                           articles_count=articles_count,
                           published_count=published_count,
                           draft_count=draft_count,
                           categories_count=categories_count,
                           tags_count=tags_count,
                           recent_articles=recent_articles,
                           title="Admin Dashboard")


@app.route('/admin/articles')
@login_required
@admin_required
def admin_articles():
    articles = Article.query.order_by(desc(Article.created_at)).all()
    return render_template('admin/dashboard.html',
                           articles=articles,
                           section="articles",
                           title="Manage Articles")


@app.route('/admin/article/new', methods=['GET', 'POST'])
@login_required
@admin_required
@log_execution_time
def new_article():
    """Упрощённое создание статьи с улучшенной обработкой ошибок и производительностью"""
    from flask_wtf import FlaskForm
    from wtforms import StringField, TextAreaField, BooleanField, SelectField, HiddenField
    from wtforms.validators import DataRequired

    class ArticleForm(FlaskForm):
        pass

    form = ArticleForm()
    categories = Category.query.all()
    tags = Tag.query.all()

    if request.method == 'POST' and form.validate_on_submit():
        try:
            logger.debug("Starting article creation process")
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            summary = request.form.get('summary', '').strip()
            published = request.form.get('published') == 'on'
            category_id = request.form.get('category_id')
            new_tags_str = request.form.get('new_tags', '').strip()

            if not title:
                flash('Заголовок обязателен!', 'danger')
                return render_template('admin/edit_article.html',
                                       form=form,
                                       categories=categories,
                                       tags=tags,
                                       is_edit=False,
                                       title="Новая статья")

            slug = request.form.get('slug', '').strip()
            if not slug:
                from slugify import slugify
                slug = slugify(title)

            if not slug or slug == '-':
                slug = f"post-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            logger.debug(f"Checking slug uniqueness: {slug}")
            base_slug = slug
            counter = 1
            while Article.query.filter_by(slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1
                logger.debug(f"Created new slug: {slug}")

            meta_title = (request.form.get('meta_title', '').strip()
                          or title)[:200]
            meta_description = request.form.get('meta_description',
                                                '').strip() or summary

            article = Article(title=title,
                              slug=slug,
                              content=content,
                              summary=summary,
                              published=published,
                              user_id=current_user.id,
                              category_id=category_id if category_id else None,
                              meta_title=meta_title,
                              meta_description=meta_description)

            logger.debug("Adding article to session")
            db.session.add(article)
            db.session.flush()

            if new_tags_str:
                logger.debug(f"Processing tags: {new_tags_str}")
                tag_names = [
                    t.strip() for t in new_tags_str.split(',') if t.strip()
                ]
                for tag_name in tag_names:
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        from slugify import slugify
                        tag_slug = slugify(tag_name)
                        if not tag_slug:
                            tag_slug = f"tag-{len(tag_name)}-{datetime.now().strftime('%Y%m%d')}"
                        tag = Tag(name=tag_name, slug=tag_slug)
                        db.session.add(tag)
                        db.session.flush()
                    article.tags.append(tag)

            logger.debug("Committing changes to database")
            db.session.commit()
            cache.clear()
            generate_sitemap()

            flash('Статья успешно создана!', 'success')
            return redirect(url_for('article', slug=article.slug))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating article: {str(e)}")
            flash(f'Ошибка при создании статьи: {str(e)}', 'danger')
            return render_template('admin/edit_article.html',
                                   form=form,
                                   categories=categories,
                                   tags=tags,
                                   is_edit=False,
                                   title="Новая статья")

    return render_template('admin/edit_article.html',
                           form=form,
                           categories=categories,
                           tags=tags,
                           is_edit=False,
                           title="Новая статья")


@app.route('/admin/article/edit/<int:article_id>', methods=['GET', 'POST'])
@login_required
@admin_required
@log_execution_time
def edit_article(article_id):
    """Упрощённое редактирование статьи с улучшенной обработкой ошибок и производительностью"""
    from flask_wtf import FlaskForm
    from wtforms import StringField, TextAreaField, BooleanField, SelectField, HiddenField
    from wtforms.validators import DataRequired

    class ArticleForm(FlaskForm):
        pass

    form = ArticleForm()
    article = Article.query.get_or_404(article_id)
    categories = Category.query.all()
    tags = Tag.query.all()

    if request.method == 'POST' and form.validate_on_submit():
        try:
            logger.debug(f"Starting article edit process for ID: {article_id}")
            title = request.form.get('title', '').strip()
            if not title:
                flash('Заголовок обязателен!', 'danger')
                return render_template(
                    'admin/edit_article.html',
                    form=form,
                    article=article,
                    categories=categories,
                    tags=tags,
                    is_edit=True,
                    title=f"Редактирование: {article.title}")

            article.title = title
            article.content = request.form.get('content', '').strip()
            article.summary = request.form.get('summary', '').strip()
            article.category_id = request.form.get('category_id') or None
            article.published = request.form.get('published') == 'on'

            new_slug = request.form.get('slug', '').strip()
            if new_slug and new_slug != article.slug:
                from slugify import slugify
                if not new_slug or new_slug == '-':
                    new_slug = f"post-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

                logger.debug(f"Checking uniqueness for new slug: {new_slug}")
                base_slug = new_slug
                counter = 1
                test_slug = new_slug
                while Article.query.filter(Article.slug == test_slug,
                                           Article.id != article.id).first():
                    test_slug = f"{base_slug}-{counter}"
                    counter += 1
                    logger.debug(f"Created new slug: {test_slug}")

                article.slug = test_slug

            article.meta_title = (request.form.get('meta_title', '').strip()
                                  or article.title)[:200]
            article.meta_description = request.form.get(
                'meta_description', '').strip() or article.summary

            logger.debug("Clearing existing tags")
            article.tags = []
            db.session.flush()

            new_tags_str = request.form.get('new_tags', '').strip()
            if new_tags_str:
                logger.debug(f"Processing tags: {new_tags_str}")
                tag_names = [
                    t.strip() for t in new_tags_str.split(',') if t.strip()
                ]
                for tag_name in tag_names:
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        from slugify import slugify
                        tag_slug = slugify(tag_name)
                        if not tag_slug:
                            tag_slug = f"tag-{len(tag_name)}-{datetime.now().strftime('%Y%m%d')}"
                        tag = Tag(name=tag_name, slug=tag_slug)
                        db.session.add(tag)
                        db.session.flush()
                    article.tags.append(tag)

            logger.debug("Committing changes to database")
            db.session.commit()
            cache.clear()
            generate_sitemap()

            flash('Статья успешно обновлена!', 'success')
            return redirect(url_for('article', slug=article.slug))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating article: {str(e)}")
            flash(f'Ошибка при обновлении статьи: {str(e)}', 'danger')
            return render_template('admin/edit_article.html',
                                   form=form,
                                   article=article,
                                   categories=categories,
                                   tags=tags,
                                   is_edit=True,
                                   title=f"Редактирование: {article.title}")

    return render_template('admin/edit_article.html',
                           form=form,
                           article=article,
                           categories=categories,
                           tags=tags,
                           is_edit=True,
                           title=f"Редактирование: {article.title}")


@app.route('/admin/article/delete/<int:article_id>', methods=['POST'])
@login_required
@admin_required
@log_execution_time
def delete_article(article_id):
    article = Article.query.get_or_404(article_id)
    try:
        db.session.delete(article)
        db.session.commit()
        cache.clear()
        generate_sitemap()
        flash('Article deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting article: {str(e)}', 'danger')

    return redirect(url_for('admin_articles'))


@app.route('/admin/categories', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_categories():
    categories = Category.query.all()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            name = request.form.get('name')
            description = request.form.get('description', '')

            if not name:
                flash('Category name is required.', 'danger')
            else:
                category = Category(name=name, description=description)
                db.session.add(category)
                try:
                    db.session.commit()
                    flash('Category created successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error creating category: {str(e)}', 'danger')

                return redirect(url_for('manage_categories'))

        elif action == 'update':
            category_id = request.form.get('category_id')
            name = request.form.get('name')
            description = request.form.get('description', '')

            category = Category.query.get_or_404(category_id)
            category.name = name
            category.description = description
            from slugify import slugify
            category.slug = slugify(name)

            try:
                db.session.commit()
                flash('Category updated successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating category: {str(e)}', 'danger')

        elif action == 'delete':
            category_id = request.form.get('category_id')
            category = Category.query.get_or_404(category_id)

            if category.articles.count() > 0:
                flash('Cannot delete category with associated articles.',
                      'danger')
            else:
                db.session.delete(category)
                try:
                    db.session.commit()
                    flash('Category deleted successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error deleting category: {str(e)}', 'danger')

        return redirect(url_for('manage_categories'))

    return render_template('admin/manage_categories.html',
                           categories=categories,
                           title="Manage Categories")


@app.route('/admin/tags', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_tags():
    tags = Tag.query.all()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            name = request.form.get('name')

            if not name:
                flash('Tag name is required.', 'danger')
            else:
                tag = Tag(name=name)
                db.session.add(tag)
                try:
                    db.session.commit()
                    flash('Tag created successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error creating tag: {str(e)}', 'danger')

                return redirect(url_for('manage_tags'))

        elif action == 'update':
            tag_id = request.form.get('tag_id')
            name = request.form.get('name')

            tag = Tag.query.get_or_404(tag_id)
            tag.name = name
            from slugify import slugify
            tag.slug = slugify(name)

            try:
                db.session.commit()
                flash('Tag updated successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating tag: {str(e)}', 'danger')

        elif action == 'delete':
            tag_id = request.form.get('tag_id')
            tag = Tag.query.get_or_404(tag_id)

            db.session.delete(tag)
            try:
                db.session.commit()
                flash('Tag deleted successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error deleting tag: {str(e)}', 'danger')

        return redirect(url_for('manage_tags'))

    return render_template('admin/manage_tags.html',
                           tags=tags,
                           title="Manage Tags")


@app.route('/sitemap.xml')
def sitemap_xml():
    response = make_response(open('static/sitemap.xml').read())
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route('/robots.txt')
def robots_txt():
    with open('static/robots.txt') as f:
        content = f.read()

    site_url = os.environ.get('SITE_URL', request.url_root.rstrip('/'))
    content = content.replace('{{site_url}}', site_url)

    response = make_response(content)
    response.headers["Content-Type"] = "text/plain"
    return response


@app.route('/admin/clear-cache')
@login_required
@admin_required
def clear_cache():
    logger.info("Clearing cache...")
    cache.clear()
    flash('Cache cleared successfully!', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', title="Page Not Found"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html', title="Server Error"), 500
```

## utils.py
```python
import os
from datetime import datetime
from flask import url_for, request
from app import app, db
from models import Article, Category, Tag

def extract_excerpt(html_content, length=150):
    """Extract a plain text excerpt from HTML content."""
    # Simple regex-based HTML tag removal (not perfect but adequate for most uses)
    import re
    text = re.sub('<[^<]+?>', '', html_content)
    text = re.sub(r'\s+', ' ', text).strip()
    
    if len(text) <= length:
        return text
    return text[:length].rsplit(' ', 1)[0] + '...'

def extract_meta_keywords(content, max_keywords=10):
    """Extract potential keywords from content."""
    # This is a very simple implementation
    # A more sophisticated approach would use NLP techniques
    import re
    from collections import Counter
    
    # Remove code blocks which won't have meaningful keywords
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    
    # Remove markdown formatting
    content = re.sub(r'[#*_~`]', ' ', content)
    
    # Tokenize and filter common words
    tokens = re.findall(r'\b[a-zA-Z][a-zA-Z0-9]{2,}\b', content.lower())
    
    # Common stop words to filter out
    stop_words = {'the', 'and', 'is', 'in', 'to', 'of', 'that', 'this', 'with', 'for', 
                  'are', 'on', 'not', 'be', 'have', 'has', 'from', 'by', 'as', 'at'}
    
    filtered_tokens = [token for token in tokens if token not in stop_words]
    
    # Count occurrences and get top keywords
    counter = Counter(filtered_tokens)
    keywords = [word for word, count in counter.most_common(max_keywords)]
    
    return ', '.join(keywords)

def generate_sitemap():
    """Generate sitemap.xml file with enhanced SEO metadata."""
    import logging
    
    try:
        logging.info("Starting enhanced sitemap generation")
        with app.app_context():
            # Get the base URL from environment variables or default to localhost
            base_url = os.environ.get('SITE_URL', 'http://localhost:5000')
            base_url = base_url.rstrip('/')
            logging.info(f"Using base URL: {base_url} for sitemap")
            
            # Create sitemap with enhanced schema support
            xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
            xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            xml_content += '        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
            xml_content += '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"\n'
            xml_content += '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"\n'
            xml_content += '        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9\n'
            xml_content += '        http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">\n'
            
            # Add home page
            now = datetime.utcnow().strftime('%Y-%m-%d')
            xml_content += f'  <url>\n    <loc>{base_url}/</loc>\n    <lastmod>{now}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
            
            # Add published articles with detailed metadata
            logging.info("Adding articles to sitemap with enhanced metadata")
            articles = Article.query.filter_by(published=True).all()
            for article in articles:
                updated = article.updated_at.strftime('%Y-%m-%d')
                
                # Skip articles with empty or placeholder slugs
                if not article.slug or article.slug == '-':
                    continue
                    
                xml_content += f'  <url>\n'
                xml_content += f'    <loc>{base_url}/blog/{article.slug}</loc>\n'
                xml_content += f'    <lastmod>{updated}</lastmod>\n'
                xml_content += f'    <changefreq>weekly</changefreq>\n'
                xml_content += f'    <priority>0.8</priority>\n'
                
                # Add news metadata for articles less than 2 days old
                days_old = (datetime.utcnow() - article.created_at).days
                if days_old < 2:
                    publication_date = article.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')
                    xml_content += f'    <news:news>\n'
                    xml_content += f'      <news:publication>\n'
                    xml_content += f'        <news:name>Developer Blog</news:name>\n'
                    xml_content += f'        <news:language>en</news:language>\n'
                    xml_content += f'      </news:publication>\n'
                    xml_content += f'      <news:publication_date>{publication_date}</news:publication_date>\n'
                    xml_content += f'      <news:title>{article.title}</news:title>\n'
                    xml_content += f'    </news:news>\n'
                
                xml_content += f'  </url>\n'
            
            # Add categories with updated lastmod dates
            logging.info("Adding categories to sitemap")
            categories = Category.query.all()
            for category in categories:
                # Find the most recent article in this category
                latest_article = Article.query.filter_by(
                    category_id=category.id, 
                    published=True
                ).order_by(Article.updated_at.desc()).first()
                
                lastmod = now
                if latest_article:
                    lastmod = latest_article.updated_at.strftime('%Y-%m-%d')
                
                xml_content += f'  <url>\n'
                xml_content += f'    <loc>{base_url}/category/{category.slug}</loc>\n'
                xml_content += f'    <lastmod>{lastmod}</lastmod>\n'
                xml_content += f'    <changefreq>weekly</changefreq>\n'
                xml_content += f'    <priority>0.6</priority>\n'
                xml_content += f'  </url>\n'
            
            # Add tags with updated lastmod dates
            logging.info("Adding tags to sitemap")
            tags = Tag.query.all()
            for tag in tags:
                # Find the most recent article with this tag
                latest_article = Article.query.join(
                    Article.tags
                ).filter(
                    Tag.id == tag.id,
                    Article.published == True
                ).order_by(Article.updated_at.desc()).first()
                
                lastmod = now
                if latest_article:
                    lastmod = latest_article.updated_at.strftime('%Y-%m-%d')
                
                xml_content += f'  <url>\n'
                xml_content += f'    <loc>{base_url}/tag/{tag.slug}</loc>\n'
                xml_content += f'    <lastmod>{lastmod}</lastmod>\n'
                xml_content += f'    <changefreq>weekly</changefreq>\n'
                xml_content += f'    <priority>0.4</priority>\n'
                xml_content += f'  </url>\n'
            
            xml_content += '</urlset>'
            
            # Write to file
            logging.info("Writing enhanced sitemap to file")
            with open('static/sitemap.xml', 'w') as f:
                f.write(xml_content)
            
            logging.info("Enhanced sitemap generation completed successfully")
            return True
    except Exception as e:
        logging.error(f"Error generating sitemap: {str(e)}")
        # Create a basic sitemap to avoid errors
        basic_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        basic_xml += f'  <url>\n    <loc>{os.environ.get("SITE_URL", "http://localhost:5000")}/</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
        basic_xml += '</urlset>'
        
        try:
            with open('static/sitemap.xml', 'w') as f:
                f.write(basic_xml)
        except:
            pass
            
        return False
```

## gunicorn_config.py
```python
"""
Конфигурация Gunicorn для оптимизации производительности и устранения проблем с сигналами

Этот файл содержит настройки для оптимизации стабильности, обработки сигналов
и предотвращения зависаний под нагрузкой.
"""

import multiprocessing
import os
import resource

# Основные настройки сервера
bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1  # Рекомендуемое количество
worker_class = "sync"  # Синхронные воркеры для максимальной стабильности
timeout = 120  # Увеличенный тайм-аут для предотвращения преждевременного убийства процессов
capture_output = True  # Перехватывать вывод для улучшенного логирования

# Предотвращение проблем с сигналами
ignore_winch = True  # Игнорировать сигнал WINCH полностью
forwarded_allow_ips = '*'  # Доверять всем заголовкам X-Forwarded-*
reuse_port = True  # Улучшает поведение при перезапуске
worker_tmp_dir = '/dev/shm'  # Использовать tmpfs для временных файлов, повышает производительность
disable_winch_logs = True  # Отключить логирование событий SIGWINCH
log_winch = False  # Дополнительный флаг отключения логирования SIGWINCH

# Основные оптимизации производительности
max_requests = 1000  # Перезапускать воркеры после обработки 1000 запросов
max_requests_jitter = 200  # Добавить случайность для предотвращения одновременного перезапуска
graceful_timeout = 30  # Время ожидания до принудительного завершения
keepalive = 5  # Сохранять соединение в течение 5 секунд после запроса

# Кастомный класс логгера для подавления WINCH сообщений
class CustomLogger:
    def setup(self, cfg):
        from gunicorn import glogging
        import logging
        
        self._logger = glogging.Logger(cfg)
        self._logger.setup(cfg)
        
        # Получаем оригинальный обработчик
        self.error_handlers = self._logger.error_handlers
        
        # Создаем фильтр для WINCH
        class WinchFilter(logging.Filter):
            def filter(self, record):
                return 'Handling signal: winch' not in record.getMessage()
                
        # Добавляем фильтр ко всем обработчикам логов
        for handler in self.error_handlers:
            handler.addFilter(WinchFilter())
    
    # Проксируем все методы к внутреннему логгеру
    def critical(self, msg, *args, **kwargs):
        self._logger.critical(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        if 'winch' not in msg.lower():
            self._logger.info(msg, *args, **kwargs)
    
    def debug(self, msg, *args, **kwargs):
        if 'winch' not in msg.lower():
            self._logger.debug(msg, *args, **kwargs)
    
    def exception(self, msg, *args, **kwargs):
        self._logger.exception(msg, *args, **kwargs)
    
    def log(self, lvl, msg, *args, **kwargs):
        if 'winch' not in msg.lower():
            self._logger.log(lvl, msg, *args, **kwargs)
    
    def access(self, resp, req, environ, request_time):
        self._logger.access(resp, req, environ, request_time)

# Логирование с улучшенной гибкостью
accesslog = "-"  # Выводить логи доступа в stdout
errorlog = "-"   # Выводить логи ошибок в stdout
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'
logger_class = 'gunicorn_config.CustomLogger'

# Отладочные возможности
reload = True  # Перезагрузка при изменении файлов
spew = False  # Включать подробное логирование трассировки (в случае необходимости отладки установите True)

# Регулирование нагрузки для предотвращения перегрузки
worker_connections = 1000  # Максимальное количество соединений на воркер
limit_request_line = 4094  # Ограничение длины строки запроса для предотвращения атак
limit_request_fields = 100  # Ограничение количества заголовков для предотвращения атак
limit_request_field_size = 8190  # Ограничение размера заголовков

# Путь к приложению
wsgi_app = "main:app"

# Дополнительные функции для улучшения стабильности
def post_fork(server, worker):
    """Выполняется после создания рабочего процесса"""
    # Устанавливаем мягкий лимит для файловых дескрипторов
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
    except (ValueError, resource.error):
        pass

def worker_int(worker):
    """Обработчик получения сигнала SIGINT"""
    # Ничего не делаем для предотвращения зависаний из-за несинхронизированного логирования
    pass

def worker_abort(worker):
    """Обработчик аварийного прерывания"""
    # Ничего не делаем для предотвращения зависаний из-за несинхронизированного логирования
    pass```

## start_server.sh
```bash
#!/bin/bash

# Скрипт для запуска Gunicorn с оптимизированными настройками
# для предотвращения зависаний и проблем с сигналами

# Функция для очистки при завершении
cleanup() {
    echo "Получен сигнал завершения. Выполняется корректное завершение..." 
    # Здесь можно добавить дополнительные команды очистки
    exit 0
}

# Регистрация обработчиков сигналов
trap cleanup SIGINT SIGTERM

# Установка переменных среды для оптимизации производительности
export GUNICORN_CMD_ARGS="--ignore-winch --preload --timeout 120 --workers 3 --max-requests 1000 --max-requests-jitter 200 --log-level info"

# Проверка наличия Python и Gunicorn
if ! command -v python3 &> /dev/null; then
    echo "Python не найден. Проверьте установку Python."
    exit 1
fi

if ! command -v gunicorn &> /dev/null; then
    echo "Gunicorn не найден. Проверьте установку Gunicorn."
    exit 1
fi

# Проверка наличия основных файлов приложения
if [ ! -f "main.py" ]; then
    echo "main.py не найден. Убедитесь, что вы находитесь в корректной директории."
    exit 1
fi

echo "Запуск Gunicorn с оптимизированной конфигурацией..."
echo "Используются настройки: $GUNICORN_CMD_ARGS"
echo "Сервер будет доступен по адресу: http://0.0.0.0:5000"

# Запуск Gunicorn с улучшенными параметрами
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app```


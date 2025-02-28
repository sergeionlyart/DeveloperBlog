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

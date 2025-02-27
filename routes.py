import os
import re
from datetime import datetime
from functools import wraps
from flask import render_template, request, redirect, url_for, flash, abort, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import desc
from app import app, db, cache
from models import User, Category, Tag, Article
from utils import generate_sitemap

# Custom decorator for admin-only routes
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
    articles = Article.query.filter_by(published=True).order_by(desc(Article.created_at)).paginate(page=page, per_page=5)
    categories = Category.query.all()
    return render_template('index.html', 
                          articles=articles, 
                          categories=categories,
                          title="Developer Blog")

@app.route('/blog/<slug>')
@cache.cached(timeout=60)
def article(slug):
    article = Article.query.filter_by(slug=slug, published=True).first_or_404()
    
    # Create breadcrumbs
    breadcrumbs = [('Home', url_for('index'))]
    if article.category:
        breadcrumbs.append((article.category.name, url_for('category', slug=article.category.slug)))
    breadcrumbs.append((article.title, ''))
    
    return render_template('article.html', 
                          article=article,
                          Article=Article,
                          breadcrumbs=breadcrumbs,
                          title=article.meta_title or article.title,
                          description=article.meta_description or article.summary)

@app.route('/category/<slug>')
@cache.cached(timeout=60)
def category(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    articles = Article.query.filter_by(category=category, published=True).order_by(desc(Article.created_at)).paginate(page=page, per_page=5)
    
    # Create breadcrumbs
    breadcrumbs = [('Home', url_for('index')), (f"Category: {category.name}", '')]
    
    return render_template('category.html', 
                          category=category, 
                          articles=articles,
                          breadcrumbs=breadcrumbs,
                          title=f"Category: {category.name}",
                          description=category.description or f"Articles in the {category.name} category.")

@app.route('/tag/<slug>')
@cache.cached(timeout=60)
def tag(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    articles = tag.articles.filter_by(published=True).order_by(desc(Article.created_at)).paginate(page=page, per_page=5)
    
    # Create breadcrumbs
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
        (Article.title.ilike(f'%{query}%') | 
         Article.content.ilike(f'%{query}%') | 
         Article.summary.ilike(f'%{query}%'))
    ).order_by(desc(Article.created_at)).paginate(page=page, per_page=5)
    
    categories = Category.query.all()
    
    # Create breadcrumbs
    breadcrumbs = [('Home', url_for('index')), (f"Search: {query}", '')]
    
    return render_template('index.html', 
                          articles=articles,
                          categories=categories,
                          search_query=query,
                          breadcrumbs=breadcrumbs,
                          title=f"Search: {query}",
                          description=f"Search results for '{query}' - find relevant developer articles and tutorials.")

# Admin routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    from app import ADMIN_USERNAME, ADMIN_PASSWORD
    from flask_wtf.csrf import validate_csrf
    from wtforms import ValidationError
    
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        # Verify CSRF token
        try:
            validate_csrf(request.form.get('csrf_token'))
        except ValidationError:
            flash('CSRF token validation failed. Please try again.', 'danger')
            return render_template('admin/login.html', title="Login")
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Проверяем с использованием статических учетных данных
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            # Если совпадает, используем существующую базу данных для получения объекта пользователя
            user = User.query.filter_by(username=username).first()
            
            # Если пользователя нет в БД (что странно, но возможно), обработаем это
            if not user:
                flash('Database error: Admin user not found.', 'danger')
                return render_template('admin/login.html', title="Login")
                
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
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    articles_count = Article.query.count()
    published_count = Article.query.filter_by(published=True).count()
    draft_count = articles_count - published_count
    categories_count = Category.query.count()
    tags_count = Tag.query.count()
    
    recent_articles = Article.query.order_by(desc(Article.created_at)).limit(5).all()
    
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
def new_article():
    """Simplified article creation with better error handling and performance"""
    categories = Category.query.all()
    tags = Tag.query.all()
    
    if request.method == 'POST':
        try:
            # Basic article data
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            summary = request.form.get('summary', '').strip()
            published = request.form.get('published') == 'on'
            category_id = request.form.get('category_id')
            
            # Validate required fields
            if not title:
                flash('Title is required!', 'danger')
                return render_template('admin/edit_article.html',
                                     categories=categories,
                                     tags=tags,
                                     is_edit=False,
                                     title="New Article")
            
            # Get or create slug
            slug = request.form.get('slug', '').strip()
            if not slug:
                from slugify import slugify
                slug = slugify(title)
            
            # Make sure slug is not empty or just a hyphen
            if not slug or slug == '-':
                slug = f"post-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
                
            # Ensure slug is unique
            base_slug = slug
            counter = 1
            while Article.query.filter_by(slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Meta info - с ограничением длины для безопасности
            meta_title = (request.form.get('meta_title', '').strip() or title)[:200]
            meta_description = request.form.get('meta_description', '').strip() or summary
            # Уже не ограничиваем длину meta_description, так как изменили тип поля на Text
            meta_keywords = (request.form.get('meta_keywords', '').strip())[:200]
            
            # Create article
            article = Article(
                title=title,
                slug=slug,
                content=content,
                summary=summary,
                published=published,
                user_id=current_user.id,
                category_id=category_id if category_id else None,
                meta_title=meta_title,
                meta_description=meta_description,
                meta_keywords=meta_keywords
            )
            
            # Add article to session
            db.session.add(article)
            db.session.flush()  # Get ID without committing
            
            # Process tags - in a simpler way
            tag_ids = request.form.getlist('tags')
            if tag_ids:
                # Use a more efficient approach
                for tag_id in tag_ids:
                    tag = Tag.query.get(tag_id)
                    if tag:
                        article.tags.append(tag)
            
            # Process new tags
            new_tags_str = request.form.get('new_tags', '').strip()
            if new_tags_str:
                tag_names = [t.strip() for t in new_tags_str.split(',') if t.strip()]
                for tag_name in tag_names:
                    # Check for existing tag
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        # Create new tag with auto-slug
                        from slugify import slugify
                        tag = Tag(name=tag_name, slug=slugify(tag_name))
                        db.session.add(tag)
                        db.session.flush()  # Get ID without committing
                    article.tags.append(tag)
            
            # Commit all changes
            db.session.commit()
            
            # Update cache and sitemap
            cache.clear()
            generate_sitemap()
            
            flash('Article created successfully!', 'success')
            return redirect(url_for('article', slug=article.slug))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating article: {str(e)}', 'danger')
            return render_template('admin/edit_article.html',
                                categories=categories,
                                tags=tags,
                                is_edit=False,
                                title="New Article")
    
    # GET request
    return render_template('admin/edit_article.html',
                        categories=categories,
                        tags=tags,
                        is_edit=False,
                        title="New Article")

@app.route('/admin/article/edit/<int:article_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_article(article_id):
    """Simplified article editing with better error handling and performance"""
    # Get article and related data
    article = Article.query.get_or_404(article_id)
    categories = Category.query.all()
    tags = Tag.query.all()
    
    if request.method == 'POST':
        try:
            # Basic article data with validation
            title = request.form.get('title', '').strip()
            if not title:
                flash('Title is required!', 'danger')
                return render_template('admin/edit_article.html',
                                     article=article,
                                     categories=categories,
                                     tags=tags,
                                     is_edit=True,
                                     title=f"Edit: {article.title}")
            
            # Update article properties
            article.title = title
            article.content = request.form.get('content', '').strip()
            article.summary = request.form.get('summary', '').strip()
            article.category_id = request.form.get('category_id') or None
            article.published = request.form.get('published') == 'on'
            
            # Update slug if explicitly provided
            new_slug = request.form.get('slug', '').strip()
            if new_slug and new_slug != article.slug:
                from slugify import slugify
                
                # Make sure slug is not empty or just a hyphen
                if not new_slug or new_slug == '-':
                    new_slug = f"post-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
                    
                # Ensure slug is unique (only if it's changing)
                base_slug = new_slug
                counter = 1
                test_slug = new_slug
                while Article.query.filter(Article.slug == test_slug, Article.id != article.id).first():
                    test_slug = f"{base_slug}-{counter}"
                    counter += 1
                    
                article.slug = test_slug
            
            # Meta info с ограничением длины для безопасности
            article.meta_title = (request.form.get('meta_title', '').strip() or article.title)[:200]
            article.meta_description = request.form.get('meta_description', '').strip() or article.summary
            # Уже не ограничиваем длину meta_description, так как изменили тип поля на Text
            article.meta_keywords = (request.form.get('meta_keywords', '').strip())[:200]
            
            # Clear existing tags (more efficient than replacing the entire collection)
            article.tags = []
            db.session.flush()
            
            # Process tags - in a simpler way
            tag_ids = request.form.getlist('tags')
            if tag_ids:
                for tag_id in tag_ids:
                    tag = Tag.query.get(tag_id)
                    if tag:
                        article.tags.append(tag)
            
            # Process new tags
            new_tags_str = request.form.get('new_tags', '').strip()
            if new_tags_str:
                tag_names = [t.strip() for t in new_tags_str.split(',') if t.strip()]
                for tag_name in tag_names:
                    # Check for existing tag
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        # Create new tag with auto-slug
                        from slugify import slugify
                        tag = Tag(name=tag_name, slug=slugify(tag_name))
                        db.session.add(tag)
                        db.session.flush()
                    article.tags.append(tag)
            
            # Commit all changes
            db.session.commit()
            
            # Update cache and sitemap
            cache.clear()
            generate_sitemap()
            
            flash('Article updated successfully!', 'success')
            return redirect(url_for('article', slug=article.slug))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating article: {str(e)}', 'danger')
    
    # GET request
    return render_template('admin/edit_article.html',
                         article=article,
                         categories=categories,
                         tags=tags,
                         is_edit=True,
                         title=f"Edit: {article.title}")

@app.route('/admin/article/delete/<int:article_id>', methods=['POST'])
@login_required
@admin_required
def delete_article(article_id):
    article = Article.query.get_or_404(article_id)
    try:
        db.session.delete(article)
        db.session.commit()
        cache.clear()  # Clear cache
        generate_sitemap()  # Regenerate sitemap
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
                flash('Cannot delete category with associated articles.', 'danger')
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

# Sitemap and robots.txt
@app.route('/sitemap.xml')
def sitemap_xml():
    response = make_response(open('static/sitemap.xml').read())
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route('/robots.txt')
def robots_txt():
    # Read robots.txt file
    with open('static/robots.txt') as f:
        content = f.read()
    
    # Replace placeholders with actual values
    site_url = os.environ.get('SITE_URL', request.url_root.rstrip('/'))
    content = content.replace('{{site_url}}', site_url)
    
    # Create response
    response = make_response(content)
    response.headers["Content-Type"] = "text/plain"
    return response

# Cache control
@app.route('/admin/clear-cache')
@login_required
@admin_required
def clear_cache():
    import logging
    logging.info("Clearing cache...")
    cache.clear()
    flash('Cache cleared successfully!', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', title="Page Not Found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html', title="Server Error"), 500

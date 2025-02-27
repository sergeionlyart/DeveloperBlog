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
    return render_template('article.html', 
                          article=article,
                          Article=Article,
                          title=article.meta_title or article.title,
                          description=article.meta_description or article.summary)

@app.route('/category/<slug>')
@cache.cached(timeout=60)
def category(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    articles = Article.query.filter_by(category=category, published=True).order_by(desc(Article.created_at)).paginate(page=page, per_page=5)
    return render_template('category.html', 
                          category=category, 
                          articles=articles,
                          title=f"Category: {category.name}")

@app.route('/tag/<slug>')
@cache.cached(timeout=60)
def tag(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    articles = tag.articles.filter_by(published=True).order_by(desc(Article.created_at)).paginate(page=page, per_page=5)
    return render_template('tag.html', 
                          tag=tag, 
                          articles=articles,
                          title=f"Tag: {tag.name}")

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
    
    return render_template('index.html', 
                          articles=articles,
                          categories=categories,
                          search_query=query,
                          title=f"Search: {query}")

# Admin routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
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
    import logging
    logging.info("Starting new_article route")
    
    try:
        logging.info("Fetching categories and tags")
        categories = Category.query.all()
        tags = Tag.query.all()
        
        if request.method == 'POST':
            logging.info("Processing POST request for new article")
            title = request.form.get('title')
            content = request.form.get('content')
            category_id = request.form.get('category_id')
            tag_ids = request.form.getlist('tags')
            published = request.form.get('published') == 'on'
            logging.info(f"Published status: {published}, Form value: {request.form.get('published')}")
            summary = request.form.get('summary', '')
            
            logging.info(f"Article data received - Title: {title}, Category ID: {category_id}")
            
            # Get or create slug
            slug = request.form.get('slug', '')
            if not slug:
                from slugify import slugify
                slug = slugify(title)
                logging.info(f"Generated slug: {slug}")
            
            # Meta info
            meta_title = request.form.get('meta_title', title)
            meta_description = request.form.get('meta_description', summary)
            meta_keywords = request.form.get('meta_keywords', '')
            
            logging.info("Creating new article object")
            # Create new article
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
            
            # Add tags
            if tag_ids:
                logging.info(f"Processing selected tags: {tag_ids}")
                selected_tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
                article.tags = selected_tags
            
            logging.info("Adding article to session")
            db.session.add(article)
            
            # Create new tags if specified
            new_tags = request.form.get('new_tags', '')
            if new_tags:
                logging.info(f"Processing new tags: {new_tags}")
                tag_names = [t.strip() for t in new_tags.split(',') if t.strip()]
                for tag_name in tag_names:
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        logging.info(f"Creating new tag: {tag_name}")
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                    article.tags.append(tag)
            
            try:
                logging.info("Committing to database")
                db.session.commit()
                logging.info("Clearing cache")
                cache.clear()  # Clear cache to reflect new content
                logging.info("Regenerating sitemap")
                generate_sitemap()  # Regenerate sitemap
                flash('Article created successfully!', 'success')
                return redirect(url_for('article', slug=article.slug))
            except Exception as e:
                logging.error(f"Error committing to database: {str(e)}")
                db.session.rollback()
                flash(f'Error creating article: {str(e)}', 'danger')
        
        logging.info("Rendering edit_article template for GET request")
        return render_template('admin/edit_article.html',
                            categories=categories,
                            tags=tags,
                            is_edit=False,
                            title="New Article")
    except Exception as e:
        logging.error(f"Unexpected error in new_article route: {str(e)}")
        flash(f'An unexpected error occurred: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/article/edit/<int:article_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_article(article_id):
    article = Article.query.get_or_404(article_id)
    categories = Category.query.all()
    tags = Tag.query.all()
    
    if request.method == 'POST':
        article.title = request.form.get('title')
        article.content = request.form.get('content')
        article.category_id = request.form.get('category_id') or None
        article.published = request.form.get('published') == 'on'
        logging.info(f"Edit published status: {article.published}, Form value: {request.form.get('published')}")
        article.summary = request.form.get('summary', '')
        
        # Update slug if explicitly provided
        new_slug = request.form.get('slug', '')
        if new_slug and new_slug != article.slug:
            article.slug = new_slug
        
        # Meta info
        article.meta_title = request.form.get('meta_title', article.title)
        article.meta_description = request.form.get('meta_description', article.summary)
        article.meta_keywords = request.form.get('meta_keywords', '')
        
        # Update tags
        tag_ids = request.form.getlist('tags')
        selected_tags = Tag.query.filter(Tag.id.in_(tag_ids)).all() if tag_ids else []
        article.tags = selected_tags
        
        # Add new tags
        new_tags = request.form.get('new_tags', '')
        if new_tags:
            tag_names = [t.strip() for t in new_tags.split(',') if t.strip()]
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                if tag not in article.tags:
                    article.tags.append(tag)
        
        try:
            db.session.commit()
            cache.clear()  # Clear cache to reflect updates
            generate_sitemap()  # Regenerate sitemap
            flash('Article updated successfully!', 'success')
            return redirect(url_for('article', slug=article.slug))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating article: {str(e)}', 'danger')
    
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
    response = make_response(open('static/robots.txt').read())
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

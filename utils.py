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

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
    """Generate sitemap.xml file."""
    import logging
    
    try:
        logging.info("Starting sitemap generation")
        with app.app_context():
            # Use a hard-coded base URL since we're outside a request context
            base_url = os.environ.get('SITE_URL', 'http://localhost:5000')
            base_url = base_url.rstrip('/')
            logging.info(f"Using base URL: {base_url} for sitemap")
            
            xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
            xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            
            # Add home page
            xml_content += f'  <url>\n    <loc>{base_url}/</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
            
            # Add published articles
            logging.info("Adding articles to sitemap")
            articles = Article.query.filter_by(published=True).all()
            for article in articles:
                updated = article.updated_at.strftime('%Y-%m-%d')
                xml_content += f'  <url>\n    <loc>{base_url}/blog/{article.slug}</loc>\n    <lastmod>{updated}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>\n'
            
            # Add categories
            logging.info("Adding categories to sitemap")
            categories = Category.query.all()
            for category in categories:
                xml_content += f'  <url>\n    <loc>{base_url}/category/{category.slug}</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.6</priority>\n  </url>\n'
            
            # Add tags
            logging.info("Adding tags to sitemap")
            tags = Tag.query.all()
            for tag in tags:
                xml_content += f'  <url>\n    <loc>{base_url}/tag/{tag.slug}</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.4</priority>\n  </url>\n'
            
            xml_content += '</urlset>'
            
            # Write to file
            logging.info("Writing sitemap to file")
            with open('static/sitemap.xml', 'w') as f:
                f.write(xml_content)
            
            logging.info("Sitemap generation completed successfully")
            return True
    except Exception as e:
        logging.error(f"Error generating sitemap: {str(e)}")
        # Create a basic sitemap to avoid errors
        basic_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        basic_xml += '  <url>\n    <loc>http://localhost:5000/</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
        basic_xml += '</urlset>'
        
        try:
            with open('static/sitemap.xml', 'w') as f:
                f.write(basic_xml)
        except:
            pass
            
        return False

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, StoryPost, Category
from datetime import datetime
from flask_caching import Cache
from sqlalchemy import func, text
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask_migrate import Migrate
from dotenv import load_dotenv

# Load environment variables from .env when present
load_dotenv()

app = Flask(__name__)
# Config from environment with sensible defaults for local development
# Use an absolute path for the default SQLite DB to avoid "unable to open database file" errors
basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(basedir, 'instance')
os.makedirs(instance_dir, exist_ok=True)

def ensure_sqlite_folder(uri: str) -> str:
    if uri and uri.startswith('sqlite:///'):
        path = uri[10:]
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
    return uri

default_sqlite = f"sqlite:///{os.path.join(instance_dir, 'story_posts.db')}"
db_uri = os.getenv('DATABASE_URL', default_sqlite)
app.config['SQLALCHEMY_DATABASE_URI'] = ensure_sqlite_folder(db_uri)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-in-production')

db.init_app(app)

# Enable schema migrations and CSRF protection
migrate = Migrate()
migrate.init_app(app, db)

# Simple cache (in-memory) to speed up index route during hosting
cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 30})
cache.init_app(app)


def clear_index_cache():
    try:
        cache.clear()
    except Exception:
        pass


# On startup, if the database is present but tables are missing (e.g. fresh deploy),
# create missing tables to avoid "no such table" runtime errors in simple deployments.
# This is a safe fallback for sqlite/local deployments and helps Render instances
# that haven't had migrations applied yet. It silently fails on error.
with app.app_context():
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if not inspector.has_table('story_posts'):
            db.create_all()
    except Exception:
        pass


# Ensure SQLite enforces foreign key constraints when used
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        # Not a SQLite DB or failed - ignore
        pass


def get_category_counts():
    rows = (
        db.session.query(StoryPost.category_id, func.count(StoryPost.id))
        .group_by(StoryPost.category_id)
        .all()
    )
    return {category_id: count for category_id, count in rows}

# Schema and default data are managed via Flask-Migrate.
# To initialize the database locally run:
#   set FLASK_APP=app.py (or $env:FLASK_APP='app.py' on PowerShell)
#   flask db init
#   flask db migrate -m "initial"
#   flask db upgrade
# To populate default categories, create a small script or Flask CLI command.

@app.route('/')
@cache.cached(timeout=30, query_string=True)
def index():
    """Display all story posts with filtering and search
    Cached briefly to reduce DB load for anonymous repeated views.
    """
    category_id = request.args.get('category', type=int)
    search_query = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'newest')
    show_favorites = request.args.get('favorites', 'false').lower() == 'true'
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = 6
    
    # Base query
    query = StoryPost.query
    
    # Apply filters
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if show_favorites:
        query = query.filter_by(is_favorite=True)
    
    if search_query:
        query = query.filter(
            (StoryPost.title.ilike(f'%{search_query}%')) |
            (StoryPost.content.ilike(f'%{search_query}%'))
        )
    
    # Apply sorting
    if sort_by == 'oldest':
        query = query.order_by(StoryPost.created_at.asc())
    elif sort_by == 'alphabetical':
        query = query.order_by(StoryPost.title.asc())
    else:  # newest (default)
        query = query.order_by(StoryPost.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    posts = pagination.items
    
    categories = Category.query.order_by(Category.name.asc()).all()
    category_counts = get_category_counts()
    selected_category = Category.query.get(category_id) if category_id else None
    
    # Calculate statistics
    total_posts = StoryPost.query.count()
    favorite_count = StoryPost.query.filter_by(is_favorite=True).count()
    
    return render_template('index.html', 
                         posts=posts, 
                         categories=categories, 
                         category_counts=category_counts,
                         selected_category=selected_category,
                         search_query=search_query,
                         sort_by=sort_by,
                         show_favorites=show_favorites,
                         pagination=pagination,
                         total_posts=total_posts,
                         favorite_count=favorite_count)


@app.route('/categories', methods=['GET', 'POST'])
def manage_categories():
    """List and create categories from the UI"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        color = request.form.get('color', '').strip() or '#6366f1'
        description = request.form.get('description', '').strip()
        if not name:
            flash('Category name is required', 'error')
            return redirect(url_for('manage_categories'))
        existing = Category.query.filter_by(name=name).first()
        if existing:
            flash('Category already exists', 'error')
            return redirect(url_for('manage_categories'))
        cat = Category(name=name, color=color, description=description)
        db.session.add(cat)
        db.session.commit()
        flash('Category created', 'success')
        clear_index_cache()
        return redirect(url_for('manage_categories'))

    categories = Category.query.order_by(Category.name.asc()).all()
    category_counts = get_category_counts()
    return render_template('categories.html', categories=categories, category_counts=category_counts)


@app.route('/categories/edit/<int:category_id>', methods=['POST'])
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '').strip() or '#6366f1'
    description = request.form.get('description', '').strip()

    if not name:
        flash('Category name is required', 'error')
        return redirect(url_for('manage_categories'))

    existing = Category.query.filter(Category.id != category_id, Category.name == name).first()
    if existing:
        flash('Category already exists', 'error')
        return redirect(url_for('manage_categories'))

    category.name = name
    category.color = color
    category.description = description
    db.session.commit()
    clear_index_cache()
    flash('Category updated successfully.', 'success')
    return redirect(url_for('manage_categories'))


@app.route('/categories/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    cat = Category.query.get_or_404(category_id)
    StoryPost.query.filter_by(category_id=category_id).update({'category_id': None})
    db.session.delete(cat)
    db.session.commit()
    clear_index_cache()
    flash('Category deleted. Stories moved to Uncategorized.', 'success')
    return redirect(url_for('manage_categories'))

@app.route('/create', methods=['GET', 'POST'])
def create_post():
    """Create a new story post"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category_id = request.form.get('category_id', type=int)
        status = request.form.get('status', 'published').strip()
        
        if not title:
            flash('Story title is required!', 'error')
            return redirect(url_for('create_post'))
        
        if not content:
            flash('Story content is required!', 'error')
            return redirect(url_for('create_post'))
        
        if len(title) > 200:
            flash('Title is too long (maximum 200 characters)!', 'error')
            return redirect(url_for('create_post'))

        if category_id and not Category.query.get(category_id):
            flash('Selected category does not exist.', 'error')
            return redirect(url_for('create_post'))

        if status not in {'draft', 'published', 'archived'}:
            status = 'published'
        
        new_post = StoryPost(title=title, content=content, category_id=category_id, status=status)
        db.session.add(new_post)
        db.session.commit()
        clear_index_cache()
        
        flash('Story saved successfully.', 'success')
        return redirect(url_for('index'))
    
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template('create_post.html', categories=categories)

@app.route('/post/<int:post_id>')
def view_post(post_id):
    """View a specific story post"""
    post = StoryPost.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post)

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    """Edit a story post"""
    post = StoryPost.query.get_or_404(post_id)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category_id = request.form.get('category_id', type=int)
        status = request.form.get('status', 'published').strip()
        
        if not title:
            flash('Story title is required!', 'error')
            return redirect(url_for('edit_post', post_id=post_id))
        
        if not content:
            flash('Story content is required!', 'error')
            return redirect(url_for('edit_post', post_id=post_id))
        
        if len(title) > 200:
            flash('Title is too long (maximum 200 characters)!', 'error')
            return redirect(url_for('edit_post', post_id=post_id))

        if category_id and not Category.query.get(category_id):
            flash('Selected category does not exist.', 'error')
            return redirect(url_for('edit_post', post_id=post_id))

        if status not in {'draft', 'published', 'archived'}:
            status = 'published'
        
        post.title = title
        post.content = content
        post.category_id = category_id
        post.status = status
        post.updated_at = datetime.utcnow()
        db.session.commit()
        clear_index_cache()
        
        flash('Story updated successfully.', 'success')
        return redirect(url_for('view_post', post_id=post_id))
    
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template('edit_post.html', post=post, categories=categories)

@app.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    """Delete a story post"""
    post = StoryPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    clear_index_cache()
    
    flash('Story deleted successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/favorite/<int:post_id>', methods=['POST'])
def toggle_favorite(post_id):
    """Toggle favorite status of a story"""
    post = StoryPost.query.get_or_404(post_id)
    post.is_favorite = not post.is_favorite
    db.session.commit()
    clear_index_cache()
    
    status = "favorite" if post.is_favorite else "unfavorite"
    flash(f'Story {status}d successfully.', 'success')
    return redirect(request.referrer or url_for('view_post', post_id=post_id))

@app.route('/api/posts')
def api_get_posts():
    """API endpoint to get all posts as JSON"""
    posts = StoryPost.query.order_by(StoryPost.created_at.desc()).all()
    return jsonify([post.to_dict() for post in posts])

@app.route('/api/posts/<int:post_id>')
def api_get_post(post_id):
    """API endpoint to get a specific post as JSON"""
    post = StoryPost.query.get_or_404(post_id)
    return jsonify(post.to_dict())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


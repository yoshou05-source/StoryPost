from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(200))
    color = db.Column(db.String(7), default='#6366f1')
    
    story_posts = db.relationship('StoryPost', back_populates='category', lazy="select")
    
    def __repr__(self):
        return f'<Category {self.name}>'

class StoryPost(db.Model):
    __tablename__ = 'story_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    category = db.relationship('Category', back_populates='story_posts')
    is_favorite = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), nullable=False, default='published')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<StoryPost {self.id}: {self.title}>'
    
    def calculate_word_count(self):
        """Calculate word count from content"""
        return len(self.content.split())
    
    def get_read_time(self):
        """Estimate read time in minutes (average 200 words per minute)"""
        word_count = self.calculate_word_count()
        minutes = max(1, round(word_count / 200))
        return minutes
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'category': self.category.name if self.category else None,
            'is_favorite': self.is_favorite,
            'status': self.status,
            'read_time': self.get_read_time(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

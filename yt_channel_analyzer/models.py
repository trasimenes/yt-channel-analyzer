from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional
from . import db


@dataclass
class Video:
    title: str
    category: str  # hero, hub, help
    view_count: int
    published_at: date


@dataclass
class Competitor:
    name: str
    videos: List[Video]
    region: Optional[str] = "Europe"  # Par défaut Europe
    industry: Optional[str] = None  # Optionnelle, peut être None
    custom_tags: Optional[List[str]] = None  # Tags personnalisés additionnels


class Concurrent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    channel_id = db.Column(db.String(100), unique=True, nullable=False)
    channel_url = db.Column(db.String(200), unique=True, nullable=False)
    thumbnail_url = db.Column(db.String(200))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    videos = db.relationship('Video', backref='concurrent', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Concurrent {self.name}>'


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    concurrent_id = db.Column(db.Integer, db.ForeignKey('concurrent.id'), nullable=False)
    
    # --- Champs de base ---
    video_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(200), nullable=False)
    publication_date = db.Column(db.DateTime)
    duration = db.Column(db.String(20)) # ex: "10:23"
    
    # --- Métriques objectives ---
    views = db.Column(db.BigInteger)
    likes = db.Column(db.Integer)
    comments = db.Column(db.Integer)
    
    # --- Analyse & Classification ---
    category = db.Column(db.String(50)) # 'hero', 'hub', 'help'
    distribution_type = db.Column(db.String(50)) # 'paid', 'organic'
    performance_score = db.Column(db.Float)
    
    # --- Critères subjectifs ---
    beauty_score = db.Column(db.Integer)
    emotion_score = db.Column(db.Integer)
    info_quality_score = db.Column(db.Integer)

    def __repr__(self):
        return f'<Video {self.title}>'

import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class users(db.Model):
    __tablename__ = 'users'
    
    _id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column("name", db.String(45), nullable=True)
    email = db.Column("email", db.String(120), nullable=False, unique=True)
    password = db.Column("password", db.String(500), nullable=False)
    age = db.Column("age", db.Integer, nullable=True)
    gender = db.Column("gender", db.String(100), nullable=True)
    about = db.Column("about", db.Text, nullable=True)
    phonen = db.Column("phonen", db.String(20), nullable=True)
    
   
    progress_records = db.relationship('UserProgress', backref='user', cascade="all, delete-orphan", lazy=True)


class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    topic_id = db.Column(db.String(50), nullable=False)
    
    is_completed = db.Column(db.Boolean, default=False)
    questions_solved = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, nullable=True) 
    
    updated_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.UniqueConstraint('user_id', 'topic_id', name='_user_topic_uc'),
    )
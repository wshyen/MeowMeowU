from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime

class Note(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # Foreign key linking notes to users

class User(db.Model, UserMixin): 
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    ps = db.Column(db.String(150), nullable=False)  
    Name = db.Column(db.String(150), nullable=False)
    secret_answer = db.Column(db.String(150), nullable=False) 
    notes = db.relationship("Note", backref="user", lazy=True)

    status = db.Column(db.String(100)) #user profile part
    birthday = db.Column(db.Date)
    mbti = db.Column(db.String(50))
    hobby = db.Column(db.String(100))
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(255), default="default_profilepic.png")
    cover_photo = db.Column(db.String(255), default="default_cover.png")
    role = db.Column(db.String(50), default='user', nullable=False)
    level1_completed = db.Column(db.Boolean, default=False)

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    image_filename = db.Column(db.String(150), nullable=False)
    caption = db.Column(db.String(255), nullable=False)
    story_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="stories")

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)  #who reported
    story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=True)  #reported story
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=True)  #reported post
    comment_id = db.Column(db.Integer, db.ForeignKey("comment.id"), nullable=True)  #reported comment
    reason = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="reports", lazy=True)
    story = db.relationship("Story", backref="reports", lazy=True)
    post = db.relationship("Post", backref="reports", lazy=True)
    comment = db.relationship("Comment", backref="reports", lazy=True)
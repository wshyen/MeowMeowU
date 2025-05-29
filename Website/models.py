from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime
from sqlalchemy import text

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

    notes = db.relationship("Note", backref="user", lazy=True, cascade="all, delete-orphan")
    stories = db.relationship("Story", backref="owner", lazy=True, cascade="all, delete-orphan")
    reports = db.relationship("Report", backref="owner", lazy=True, cascade="all, delete-orphan")

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

    user = db.relationship("User", backref=db.backref("user_stories", lazy=True, cascade="all, delete-orphan"))

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=True)
    post_id = db.Column(db.Integer, nullable=True)
    comment_id = db.Column(db.Integer, nullable=True)
    reason = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("user_reports", lazy=True, cascade="all, delete-orphan"))
    story = db.relationship("Story", backref="reports", lazy=True)

    @property
    def report_type(self):
        if self.story_id and not db.session.execute(text("SELECT id FROM story WHERE id = :story_id"), {"story_id": self.story_id}).fetchone():
            return "Deleted Successfully"
        elif self.post_id and not db.session.execute(text("SELECT post_id FROM post WHERE post_id = :post_id"), {"post_id": self.post_id}).fetchone():
            return "Deleted Successfully"
        elif self.comment_id and not db.session.execute(text("SELECT id FROM comment WHERE id = :comment_id"), {"comment_id": self.comment_id}).fetchone():
            return "Deleted Successfully"
        elif self.story_id:
            return "Story"
        elif self.comment_id and self.post_id:
            return "Comment"
        elif self.post_id:
            return "Post"
        return "Deleted Successfully"

    @property
    def view_action(self):
        if self.comment_id and self.post_id:
            return ("auth.view_post", {"post_id": self.post_id}, "View Comment") if db.session.execute(text("SELECT id FROM comment WHERE id = :comment_id"), {"comment_id": self.comment_id}).fetchone() else (None, {}, "Deleted Successfully")
        elif self.post_id and not self.comment_id:
            return ("auth.view_post", {"post_id": self.post_id}, "View Post") if db.session.execute(text("SELECT post_id FROM post WHERE post_id = :post_id"), {"post_id": self.post_id}).fetchone() else (None, {}, "Deleted Successfully")
        elif self.story_id:
            return ("auth.view_story", {"story_id": self.story_id}, "View Story") if db.session.execute(text("SELECT id FROM story WHERE id = :story_id"), {"story_id": self.story_id}).fetchone() else (None, {}, "Deleted Successfully")
        return (None, {}, "")
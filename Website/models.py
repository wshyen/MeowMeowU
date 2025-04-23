from . import db
from flask_login import UserMixin  #import UserMixin for user authentication support
from sqlalchemy.sql import func

class Note(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  #foreign key linking notes to users

class User(db.Model, UserMixin): 
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    ps = db.Column(db.String(150), nullable=False)  
    UserName = db.Column(db.String(150), nullable=False)  
    secret_answer = db.Column(db.String(150), nullable=False) 
    notes = db.relationship("Note", backref="user", lazy=True)
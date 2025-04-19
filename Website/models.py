from . import db
from flask_login import UserMixin #import UserMixin for user authentication support
from sqlalchemy.sql import func

class Note(db.Model): #define a database model (table) for storing "Note" information
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now()) #timestamp of when the note was created, defaults to the current time
    user_id = db.Column(db.Integer, db.ForeignKey("user.id")) #linking the note to a specific user by their ID (user.id)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True)
    ps = db.Column(db.String(150)) #hashed password for the user
    UserName = db.Column(db.String(150)) #allows accessing all notes for the user, (link to note model)
    notes = db.relationship("Note")
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path

db = SQLAlchemy()
DB_NAME = "datebase.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = "Hello"
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_NAME}"
    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, urlprefix="/")
    app.register_blueprint(auth, urlprefix="/")

    from .models import User, Note #import this to make sure models.py file run before we initialize database

    return app

def create_database(app):
    if not path.exists("Website/" + DB_NAME):
        db.create_all(app=app)
        print("Created database!")


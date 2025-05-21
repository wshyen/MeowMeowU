from flask import Flask
from flask_sqlalchemy import SQLAlchemy #SQLAlchemy is used for database operations
from os import path #path is used for file system checks
from flask_login import LoginManager
from flask_migrate import Migrate
from sqlalchemy.sql import text

db = SQLAlchemy() #initialize SQLAlchemy instance for database handling
DB_NAME = "datebase.db" #name the file
migrate = Migrate()

def create_app(): #a function to create and configure the Flask app
    app = Flask(__name__) #create Flask app
    app.config['SECRET_KEY'] = "Hello"
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_NAME}" #path to database
    
    db.init_app(app) #initialize the database with the Flask app
    migrate.init_app(app, db)

    #enable Write-Ahead Logging (WAL),to minimizes database locking issues
    def setup_wal():
        with db.engine.connect() as connection:
            connection.execute(text("PRAGMA journal_mode=WAL;"))
    
    #import views and auth Blueprint, views handle general routes and auth handle authentication routes
    from .views import views
    from .auth import auth
    from .search import search_bp
    from .catprofile import catprofile_bp
    from .community import community_bp
    from .contestmanagement import contestmanagement_bp
    from .quizfeature import quiz_bp
    from .relationship import relationship_bp

    #register Blueprints with the app
    app.register_blueprint(views, urlprefix="/")
    app.register_blueprint(auth, urlprefix="/")
    app.register_blueprint(search_bp, urlprefix="/")
    app.register_blueprint(catprofile_bp, urlprefix="/")
    app.register_blueprint(community_bp, urlprefix="/")
    app.register_blueprint(contestmanagement_bp, urlprefix="/")
    app.register_blueprint(quiz_bp, urlprefix="/")
    app.register_blueprint(relationship_bp, url_prefix="/relationship")


    from .models import User, Note #import this to make sure models.py file run before we initialize database

    create_database(app) #create the database if it doesn't already exist

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app

def create_database(app): #func to create a database
    if not path.exists("Website/" + DB_NAME):
        with app.app_context(): #use app context for db.create_all()
            db.create_all() #create all tables defined in the models
        print("Created database!")
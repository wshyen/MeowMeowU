from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy
DB_NAME = "datebase.db"

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "Hello"
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, urlprefix="/")
    app.register_blueprint(auth, urlprefix="/")

    return app
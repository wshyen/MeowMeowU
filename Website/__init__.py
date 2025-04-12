from flask import Flask

def create_app():
    app = Flask(__main__)
    app.config["SECRET_KEY"] = "Hello"

    return app
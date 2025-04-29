import sqlite3
from flask import Blueprint, Flask, request, redirect, render_template
from flask_login import current_user

community_bp = Blueprint('community', __name__, template_folder='templates', static_folder='static')

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'datebase.db')
    db_path = os.path.abspath(db_path) 
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@community_bp.route('/community-feature')
def community_feature():
    return render_template("community_index.html", user=current_user)


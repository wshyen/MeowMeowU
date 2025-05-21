import sqlite3
from flask import Blueprint, g, render_template

relationship_bp = Blueprint('relationship', __name__, template_folder='templates')

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'datebase.db')
    db_path = os.path.abspath(db_path) 
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


import sqlite3
import os
from flask import Blueprint, render_template, request
from flask_login import current_user

search_bp = Blueprint('search', __name__, template_folder='templates', static_folder='static')

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'datebase.db')
    db_path = os.path.abspath(db_path) 
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@search_bp.route('/search-feature')
def search_feature():
    return render_template("search_feature.html", user=current_user)

@search_bp.route('/cat_list')
def cat_list():
    name = request.args.get("name", "").lower()
    gender = request.args.get("gender", "")
    color = request.args.get("color", "")
    sort = request.args.get("sort")

    print(f"Name: {name}, Gender: {gender}, Color: {color}, Sort: {sort}")

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM profiles WHERE 1=1"
    cat_filters = []

    if name:
        query += " AND LOWER(name) LIKE ?"
        cat_filters.append(f"%{name}%")

    if gender and gender != "Any":
        query += " AND gender = ?"
        cat_filters.append(gender)

    if color:
        query += " AND color = ?"
        cat_filters.append(color)

    if sort == "name_asc":
        query += " ORDER BY name ASC"
    elif sort == "name_desc":
        query += " ORDER BY name DESC"

    cursor.execute(query, cat_filters)
    profiles = cursor.fetchall()
    conn.close()

    if profiles:
        return render_template("cat_list.html", profiles=profiles, user=current_user)
    else:
        return render_template("cat_list.html", message="No cats found matching your criteria.", user=current_user)

 
@search_bp.route('/single_profile')
def single_profile():
    name = request.args.get("name", "").lower()
    selected_cat = None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE LOWER(name) = ?", (name.lower(),))
    selected_cat = cursor.fetchone()
    conn.close()

    if selected_cat:
        return render_template("single_profile.html", cat=selected_cat, user=current_user)
    
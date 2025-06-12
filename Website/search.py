import sqlite3
import os
from flask import Blueprint, render_template, request, url_for, redirect
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
    search_type = request.args.get('search_type', '')
    keyword = request.args.get('keyword', '')
    gender = request.args.get('gender', '')
    color = request.args.get('color', '')
    sort = request.args.get('sort', '')

    if not search_type and not keyword:
        return render_template('search_feature.html', user=current_user) 

    if search_type == 'user':
        return redirect(url_for('search.user_result', search_type="user", keyword=keyword))
    elif search_type == 'post':
        return redirect(url_for('search.post_result', search_type="post", keyword=keyword))
    else:
        return redirect(url_for('search.cat_result', search_type="cat", keyword=keyword, gender=gender, color=color, sort=sort))
    
@search_bp.route('/user_result')
def user_result():
    keyword = request.args.get("keyword", "").lower()
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM user WHERE 1=1"
    user_filters = []

    if keyword:
        query += " AND LOWER(Name) LIKE ?"
        user_filters.append(f"%{keyword}%")

    cursor.execute(query, user_filters)
    users = cursor.fetchall()
    conn.close()

    if users:
        return render_template("search_result.html", search_type="user", keyword=keyword, users=users, user=current_user)
    else:
        return render_template("search_result.html", search_type="user", keyword=keyword, message="No users found matching your criteria:", user=current_user)

@search_bp.route('/post_result')
def post_result():
    keyword = request.args.get("keyword", "").lower()
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT post.*, user.name, user.profile_picture
        FROM post
        JOIN user ON post.user_id = user.id
        WHERE LOWER(post.content) LIKE ?
        ORDER BY post.post_id DESC
    '''

    cursor.execute(query, (f"%{keyword}%",)) 
    posts = cursor.fetchall()
    conn.close()

    if posts:
        return render_template("search_result.html", search_type="post", keyword=keyword, posts=posts, user=current_user)
    else:
        return render_template("search_result.html", search_type="post", keyword=keyword, message="No posts found matching your criteria:", user=current_user)

@search_bp.route('/cat_result')
def cat_result():
    keyword = request.args.get("keyword", "").lower()
    gender = request.args.get("gender", "")
    color = request.args.get("color", "")
    sort = request.args.get("sort")

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM profiles WHERE 1=1"
    cat_filters = []

    if keyword:
        query += " AND LOWER(name) LIKE ?"
        cat_filters.append(f"%{keyword}%")

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
        return render_template("search_result.html", search_type="cat", keyword=keyword, profiles=profiles, user=current_user)
    else:
        return render_template("search_result.html", search_type="cat", keyword=keyword, message="No cats found matching your criteria:", user=current_user)

 
@search_bp.route('/single_profile')
def single_profile():
    name = request.args.get("name", "").lower()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE LOWER(name) = ?", (name,))
    cat = cursor.fetchone()
    conn.close()

    if cat:
        return render_template("single_profile.html", cat=cat, user=current_user)
    
    return redirect(url_for("views.home"))
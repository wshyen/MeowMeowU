import sqlite3
import os
from flask import Blueprint, Flask, request, redirect, render_template, url_for
from flask_login import current_user, login_required

from werkzeug.utils import secure_filename 
from datetime import datetime

community_bp = Blueprint('community', __name__, template_folder='templates', static_folder='static')

UPLOAD_FOLDER = os.path.join('community', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'datebase.db')
    db_path = os.path.abspath(db_path) 
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@community_bp.route('/community-feature')
def community_feature():
      conn =get_db_connection()
      post = conn.execute ('SELECT * FROM post ORDER BY created_at DESC').fetchall()
      conn.close()
      return render_template("community_index.html", user=current_user, posts=post)

@community_bp.route('/post/create', methods=['POST'])
@login_required
def create_post():
    content = request.form['content']
    username = current_user.username
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    image = request.files.get('image')
    image_path = None

    if image and allowed_file(image.filename):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(image.filename)
        image.save(os.path.join(UPLOAD_FOLDER, filename))
        image_path = f"uploads/{filename}"

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO post (username, content, image_path, created_at) VALUES (?, ?, ?, ?)',
        (username, content, image_path, created_at)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('community.community_feature'))

@community_bp.route('/post/like/<int:post_id>') 
def like_post(post_id):
    conn = get_db_connection()
    conn.execute('UPDATE post SET like_count = like_count + 1 WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('community.community_feature'))
import os
import sqlite3
from datetime import datetime
from flask import Blueprint, Flask, request, redirect, render_template, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename 

community_bp = Blueprint('community', __name__, template_folder='templates')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'posts')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'datebase.db')
    db_path = os.path.abspath(db_path) 
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@community_bp.route('/community-feature')
def community_feature():
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT post.*, user.username, 
               COUNT(likes.id) AS like_count
        FROM post 
        JOIN user ON post.user_id = user.id 
        LEFT JOIN likes ON post.post_id = likes.post_id
        GROUP BY post.post_id
        ORDER BY post.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template("community_index.html", user=current_user, posts=posts)

@community_bp.route('/post/create', methods=['POST'])
@login_required
def create_post():
    content = request.form['content']
    user_id = current_user.id
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    media = request.files.get('media')
    media_url = None

    if media and allowed_file(media.filename):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(media.filename)
        media.save(os.path.join(UPLOAD_FOLDER, filename))
        media_url = f"posts/{filename}"
        print("File saved to:", os.path.join(UPLOAD_FOLDER, filename))

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO post (user_id, content, media_url, created_at) VALUES (?, ?, ?, ?)', (user_id, content, media_url, created_at)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('community.community_feature'))

@community_bp.route('/post/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    user_id = current_user.id

    conn = get_db_connection()

    # Check if the post has already been liked to avoid duplicate likes
    existing_like = conn.execute(
        'SELECT 1 FROM likes WHERE user_id = ? AND post_id = ?',
        (user_id, post_id)
    ).fetchone()

    if not existing_like:
        conn.execute(
            'INSERT INTO likes (user_id, post_id) VALUES (?, ?)',
            (user_id, post_id)
        )
        conn.commit()

    conn.close()
    return redirect(url_for('community.community_feature'))
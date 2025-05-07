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

@community_bp.route('/community_feature')
def community_feature():
    conn = get_db_connection()

    posts = conn.execute('''
    SELECT 
        post.*, 
        user.username, 
        user.profile_picture,
        COUNT(likes.id) AS like_count,
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM likes 
                WHERE likes.post_id = post.post_id AND likes.user_id = ?
            ) THEN 1
            ELSE 0
        END AS liked_by_current_user
    FROM post 
    JOIN user ON post.user_id = user.id 
    LEFT JOIN likes ON post.post_id = likes.post_id
    GROUP BY post.post_id
    ORDER BY post.created_at DESC
''', 
(current_user.id if current_user.is_authenticated else -1,)
).fetchall()

    conn.close()
    return render_template("community_index.html", user=current_user, posts=posts)

@community_bp.route('/post/<int:post_id>')
def post_detail(post_id):
    conn = get_db_connection()
    
    post = conn.execute('''
        SELECT 
            post.*, 
            user.username,
            user.profile_picture,
             (SELECT COUNT(*) FROM likes WHERE likes.post_id = post.post_id) AS like_count,
            CASE 
                WHEN EXISTS (
                    SELECT 1 FROM likes 
                    WHERE likes.post_id = post.post_id AND likes.user_id = ?
                ) THEN 1
                ELSE 0
            END AS liked_by_current_user
        FROM post 
        JOIN user ON post.user_id = user.id
        WHERE post.post_id = ?
    ''', (
        current_user.id if current_user.is_authenticated else -1,
        post_id
    )).fetchone()

    conn.close()
    return render_template("community_detail.html", post=post, user=current_user)

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


#My Post

@community_bp.route('/my-posts')
@login_required
def my_posts():
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT post.*, user.username,
               COUNT(likes.id) AS like_count
        FROM post
        JOIN user ON post.user_id = user.id
        LEFT JOIN likes ON post.post_id = likes.post_id
        WHERE post.user_id = ?
        GROUP BY post.post_id
        ORDER BY post.created_at DESC
    ''', (current_user.id,)).fetchall()
    conn.close()
    return render_template("my_posts.html", user=current_user, posts=posts)

@community_bp.route('/post/edit/<int:post_id>', methods=['POST'])
@login_required
def edit_post(post_id):
    content = request.form['content']
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM post WHERE post_id = ?', (post_id,)).fetchone()

    if post and post['user_id'] == current_user.id:
        conn.execute('UPDATE post SET content = ? WHERE post_id = ?', (content, post_id))
        conn.commit()

    conn.close()
    return redirect(url_for('community.my_posts'))

@community_bp.route('/post/delete/<int:post_id>', methods=['POST'])  # Route to delete a post, accepts only POST requests
@login_required  # Ensures the user must be logged in to delete a post
def delete_post(post_id):
    conn = get_db_connection()

    # Retrieve the post data from the database
    post = conn.execute('SELECT * FROM post WHERE post_id = ?', (post_id,)).fetchone()

    # Check if the post exists and belongs to the current user
    if post and post['user_id'] == current_user.id:
        # Delete the post from the database
        conn.execute('DELETE FROM post WHERE post_id = ?', (post_id,))
        conn.commit()

    conn.close()
    # Redirect back to the community feature page after deletion
    return redirect(url_for('community.community_feature'))


# Like

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
    referer = request.referrer

    if '/community' in referer :
        return redirect(url_for('community.community_feature'))

    return redirect(url_for('community.post_detail', post_id=post_id))

@community_bp.route('/post/unlike/<int:post_id>', methods=['POST'])
@login_required
def unlike_post(post_id):
    user_id = current_user.id

    conn = get_db_connection()
    conn.execute(
        'DELETE FROM likes WHERE user_id = ? AND post_id = ?',
        (user_id, post_id)
    )
    conn.commit()
    conn.close()

    referer = request.referrer

    if '/community' in referer :
        return redirect(url_for('community.community_feature'))

    return redirect(url_for('community.post_detail', post_id=post_id))
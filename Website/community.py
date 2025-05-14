import os
import sqlite3
from datetime import datetime
from flask import Blueprint, request,flash, redirect, render_template, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename 


community_bp = Blueprint('community', __name__, template_folder='templates')

POSTS_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'posts')
COMMENTS_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'comments')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'datebase.db')
    db_path = os.path.abspath(db_path) 
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_cat_names():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'cat_profiles.db')
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT name FROM profiles')
    cat_names = [row['name'] for row in cursor.fetchall()]

    conn.close()
    return cat_names


# All Posts
@community_bp.route('/community_feature')
def community_feature(): 
    user_id = current_user.id if current_user.is_authenticated else -1
    sort = request.args.get('sort', 'date_desc') 
   
    if sort == 'date_asc': 
        order_by = 'post.created_at ASC'
    elif sort == 'date_desc':
        order_by = 'post.created_at DESC'
    elif sort == 'likes_desc':
        order_by = 'like_count DESC'
    
    else:
        order_by = 'post.user_id'
    
    conn = get_db_connection()

    query = f'''
        SELECT post.*, user.name, user.profile_picture,
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
        ORDER BY {order_by}
    '''
    posts = conn.execute(query, (user_id,)).fetchall()
    conn.close()

    return render_template("community_index.html", user=current_user, posts=posts, sort=sort, cat_names=get_cat_names())


# Post Detail
@community_bp.route('/post/<int:post_id>')
def post_detail(post_id):
    conn = get_db_connection()
    
    post = conn.execute('''
        SELECT 
            post.*, 
            user.name,
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

    comments = conn.execute('''
        SELECT 
            comment.*,
            user.name AS name, 
            user.profile_picture AS profile_picture,
            (SELECT COUNT(*) FROM comment_like WHERE comment_like.comment_id = comment.id) AS like_count,
            CASE 
                WHEN EXISTS (
                    SELECT 1 FROM comment_like 
                    WHERE comment_like.comment_id = comment.id AND comment_like.user_id = ?
                ) THEN 1
                ELSE 0
            END AS liked_by_current_user
        FROM comment
        JOIN user ON comment.user_id = user.id
        WHERE comment.post_id = ?
        ORDER BY comment.created_at DESC
    ''', (current_user.id if current_user.is_authenticated else -1, post_id)).fetchall()

    conn.close()

    return render_template("community_detail.html", post=post, comments=comments, user=current_user)


# Create Post
@community_bp.route('/post/create', methods=['POST'])
def create_post():
    if not current_user.is_authenticated:
        flash("You must be logged in to view result!", category="error")
        return redirect(url_for('auth.login'))
    
    content = request.form['content']
    cat_hashtag = request.form.get('cat_hashtag')
    user_id = current_user.id
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    media = request.files.get('media')
    media_url = None

    if media and allowed_file(media.filename):
        os.makedirs(POSTS_FOLDER, exist_ok=True)
        filename = secure_filename(media.filename)
        media.save(os.path.join(POSTS_FOLDER, filename))
        media_url = f"posts/{filename}"
        print("File saved to:", os.path.join(POSTS_FOLDER, filename))

    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO post (user_id, content, media_url, created_at, cat_hashtag)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (user_id, content, media_url, created_at, cat_hashtag)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('community.community_feature'))


# Hashtag Posts
@community_bp.route('/hashtag/<string:hashtag>')
def hashtag_posts(hashtag):
    sort = request.args.get('sort', 'date_desc')

    conn = get_db_connection()

    if sort == 'date_asc':
        order_by = 'post.created_at ASC'
    elif sort == 'date_desc':
        order_by = 'post.created_at DESC'
    elif sort == 'likes_desc':
        order_by = 'like_count DESC'
    else:
        order_by = 'post.created_at DESC'

    posts = conn.execute(
        f'''
        SELECT post.*, user.name, user.profile_picture,
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
        WHERE post.cat_hashtag = ?
        GROUP BY post.post_id
        ORDER BY {order_by}
        ''',
        (current_user.id if current_user.is_authenticated else -1, hashtag)
    ).fetchall()

    conn.close()

    return render_template('community_index.html',user=current_user, posts=posts, sort=sort, cat_names=get_cat_names())



#My Post
@community_bp.route('/my-posts')
def my_posts():
    if not current_user.is_authenticated:
        flash("You must be logged in to view result!", category="error")
        return redirect(url_for('auth.login'))
    
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT post.*, user.name, user.profile_picture,
            COUNT(likes.id) AS like_count
        FROM post
        JOIN user ON post.user_id = user.id
        LEFT JOIN likes ON post.post_id = likes.post_id
        WHERE post.user_id = ?
        GROUP BY post.post_id
        ORDER BY post.created_at DESC
    ''', (current_user.id,)).fetchall()
    conn.close()
    return render_template("my_posts.html", user=current_user, posts=posts, cat_names=get_cat_names())


# Edit and Delete Post
@community_bp.route('/post/edit/<int:post_id>', methods=['POST'])
def edit_post(post_id):
    content = request.form['content']
    cat_hashtag = request.form.get('cat_hashtag')
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM post WHERE post_id = ?', (post_id,)).fetchone()

    if post and post['user_id'] == current_user.id:
        conn.execute(
            'UPDATE post SET content = ?, cat_hashtag = ? WHERE post_id = ?',
            (content, cat_hashtag, post_id)
        )
        conn.commit()
        
    print("Request received:", request.form)
    print("Edit post request received for post_id:", post_id)
    conn.close()
    return redirect(url_for('community.my_posts'))

@community_bp.route('/post/delete/<int:post_id>', methods=['POST'])  # Route to delete a post, accepts only POST requests
def delete_post(post_id):
    conn = get_db_connection()

    # Retrieve the post data from the database
    post = conn.execute('SELECT * FROM post WHERE post_id = ?', (post_id,)).fetchone()

    # Check if the post exists and belongs to the current user
    if post and post['user_id'] == current_user.id:
        # Delete the post from the database
        conn.execute('DELETE FROM post WHERE post_id = ?', (post_id,))
        conn.commit()

    if post['media_url']:
        file_path = os.path.join(os.path.dirname(__file__), 'static', post['media_url'])
        if os.path.exists(file_path):
            os.remove(file_path)

    conn.close()
    # Redirect back to the community feature page after deletion
    return redirect(url_for('community.my_posts'))


# Like and Unlike Post
@community_bp.route('/post/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    if not current_user.is_authenticated:
        flash("You must be logged in to like post!", category="error")
        return redirect(url_for('auth.login')) 
    
    user_id = current_user.id
    sort = request.form.get('sort', 'date_desc')

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

    if 'community_feature' in referer or '/community_feature' in referer:
        return redirect(url_for('community.community_feature', sort=sort))
    
    return redirect(url_for('community.post_detail', post_id=post_id))

@community_bp.route('/post/unlike/<int:post_id>', methods=['POST'])
def unlike_post(post_id):
    user_id = current_user.id
    sort = request.form.get('sort', 'date_desc')

    conn = get_db_connection()
    conn.execute(
        'DELETE FROM likes WHERE user_id = ? AND post_id = ?',
        (user_id, post_id)
    )
    conn.commit()
    conn.close()

    referer = request.referrer

    if 'community_feature' in referer or '/community_feature' in referer:
        return redirect(url_for('community.community_feature', sort=sort))

    return redirect(url_for('community.post_detail', post_id=post_id))

# comment
@community_bp.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    if not current_user.is_authenticated:
        flash("You must be logged in to comment!", category="error")
        return redirect(url_for('auth.login')) 
    
    content = request.form.get('content', '').strip() 
    media = request.files.get('media')
    media_url = None
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_id = current_user.id
    sort = request.form.get('sort', 'date_desc')

    if not content and not media:
        flash("You must provide either text or media for your comment!", category="error")
        return redirect(f'/post/{post_id}#comments')

    if media and allowed_file(media.filename):
        os.makedirs(COMMENTS_FOLDER, exist_ok=True)
        filename = secure_filename(media.filename)
        media.save(os.path.join(COMMENTS_FOLDER, filename))
        media_url = f"comments/{filename}"
        print("File saved to:", os.path.join(COMMENTS_FOLDER, filename))
    
    conn = get_db_connection()
    conn.execute(
        '''INSERT INTO comment (content, media_url, created_at, post_id, user_id) 
           VALUES (?, ?, ?, ?, ?)''', 
        (content, media_url, created_at, post_id, user_id) 
    )
    conn.commit()
    conn.close()

    return redirect(f'/post/{post_id}#comments')

@community_bp.route('/comment/like/<int:comment_id>', methods=['POST'])
def like_comment(comment_id):
    if not current_user.is_authenticated:
        flash("You must be logged in to like a comment!", category="error")
        return redirect(url_for('auth.login')) 
    
    user_id = current_user.id
    conn = get_db_connection()

    result = conn.execute(
        'SELECT post_id FROM comment WHERE id = ?',
        (comment_id,)
    ).fetchone()
    post_id = result['post_id']

    existing_like = conn.execute(
        'SELECT 1 FROM comment_like WHERE user_id = ? AND comment_id = ?',
        (user_id, comment_id)
    ).fetchone()

    if not existing_like:
        conn.execute(
            'INSERT INTO comment_like (user_id, comment_id, post_id) VALUES (?, ?, ?)',
            (user_id, comment_id, post_id)
        )
        conn.commit()

    conn.close()
    return redirect(url_for('community.post_detail', post_id=post_id))

@community_bp.route('/comment/unlike/<int:comment_id>', methods=['POST'])
def unlike_comment(comment_id):
    user_id = current_user.id
    conn = get_db_connection()

    result = conn.execute(
        'SELECT post_id FROM comment WHERE id = ?',
        (comment_id,)
    ).fetchone()

    post_id = result['post_id']

    conn.execute(
        'DELETE FROM comment_like WHERE user_id = ? AND comment_id = ?',
        (user_id, comment_id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('community.post_detail', post_id=post_id))
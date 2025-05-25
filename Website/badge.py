import os
import sqlite3
from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'
badge_bp = Blueprint('badge', __name__)

UPLOAD_FOLDER = 'Website/static/badges' #Folder to store uploaded files
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'datebase.db')
    db_path = os.path.abspath(db_path) 
    conn = sqlite3.connect(db_path)  
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def initialize_database():
    with get_db_connection() as conn:
        #Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON;") 

        conn.execute('''
            CREATE TABLE IF NOT EXISTS badge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                criteria TEXT NOT NULL,
                icon TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_badge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                badge_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (badge_id) REFERENCES badge(id)
            )
        ''')
        conn.commit()

#User badge gallery
@badge_bp.route('/badges')
@login_required
def badge_gallery():
    user_role = getattr(current_user, 'role', None)
    conn = get_db_connection()
    badges = conn.execute('SELECT * FROM badge').fetchall()
    user_badges = conn.execute('SELECT badge_id FROM user_badge WHERE user_id = ?', (current_user.id,)).fetchall()
    user_badges_ids = {row['badge_id'] for row in user_badges}
    
    user = conn.execute('SELECT * FROM user WHERE id = ?', (current_user.id,)).fetchone()
    claimable_badge_ids = set()
    for badge in badges:
        #if user has completed level 1 quiz, they can claim the quiz_level1 badge
        if badge['criteria'] == 'quiz_level1' and user['level1_completed'] and badge['id'] not in user_badges_ids:
            claimable_badge_ids.add(badge['id'])
        #if user has completed level 2 quiz, they can claim the quiz_level2 badge
        if badge['criteria'] == 'quiz_level2' and user['level2_completed'] and badge['id'] not in user_badges_ids:
            claimable_badge_ids.add(badge['id'])
        #if user has won contest 1, they can claim the contest_winner_1 badge
        if badge['criteria'] == 'contest_winner_{contest_id}' and getattr(user, 'contest1_winner', 0) and badge['id'] not in user_badges_ids:
            claimable_badge_ids.add(badge['id'])
        #Add more for other badges as needed

    conn.close()
    return render_template('badge_gallery.html', user_role=user_role, all_badges=badges, user_badges_ids=user_badges_ids, claimable_badge_ids= claimable_badge_ids, user=current_user)

#Single badge page
@badge_bp.route('/badge/<int:badge_id>')
@login_required
def badge(badge_id):
    conn = get_db_connection()
    winner = conn.execute('SELECT * FROM user WHERE id = ?', (current_user.id,)).fetchone()
    badge = conn.execute('SELECT * FROM badge WHERE id = ?', (badge_id,)).fetchone()
    already_claimed = conn.execute(
        'SELECT 1 FROM user_badge WHERE user_id = ? AND badge_id = ?', (current_user.id, badge_id)
    ).fetchone()
    conn.close()
    reason = request.args.get('reason', 'generic')
    return render_template('badge.html', badge=badge, reason=reason, user=current_user, already_claimed=already_claimed, winner= winner)

#Claim badge (quiz/contest)
@badge_bp.route('/claim_badge/<int:badge_id>', methods=['POST'])
@login_required
def claim_badge(badge_id):
    conn = get_db_connection()
    already_claimed = conn.execute(
        'SELECT 1 FROM user_badge WHERE user_id = ? AND badge_id = ?', (current_user.id, badge_id)
    ).fetchone()
    reason = request.args.get('reason', 'generic')
    if already_claimed:
        flash('You have already claimed this badge!', 'error')
    else:
        conn.execute(
            'INSERT INTO user_badge (user_id, badge_id) VALUES (?, ?)', (current_user.id, badge_id)
        )
        conn.commit()
        flash('Badge claimed successfully!', 'success')
    conn.close()
    return redirect(url_for('badge.badge_gallery'))

#Award a badge to the user if they meet the criteria
def award_badge_if_eligible(user_id, criteria):
    conn = get_db_connection()
    badge = conn.execute('SELECT * FROM badge WHERE criteria = ?', (criteria,)).fetchone()
    if badge:
        already_claimed = conn.execute(
            'SELECT 1 FROM user_badge WHERE user_id = ? AND badge_id = ?', (user_id, badge['id'])
        ).fetchone()
        if not already_claimed:
            conn.execute(
                'INSERT INTO user_badge (user_id, badge_id) VALUES (?, ?)', (user_id, badge['id'])
            )
            conn.commit()
    conn.close()

#Award badge to user based on likes
def check_like_badges(user_id):
    conn = get_db_connection()
    count = conn.execute(
        'SELECT COUNT(*) FROM likes WHERE user_id = ?', (user_id,)).fetchone()[0]
    for milestone in [10, 50, 100]:
        if count >= milestone:
            award_badge_if_eligible(user_id, f'likes_{milestone}_post')
    conn.close()

#Award badge to user based on comments
def check_comment_badges(user_id):
    conn = get_db_connection()
    count = conn.execute(
        'SELECT COUNT(*) FROM comment WHERE user_id = ?', (user_id,)).fetchone()[0]
    for milestone in [10, 50, 100]:
        if count >= milestone:
            award_badge_if_eligible(user_id, f'comment_{milestone}_post')
    conn.close()

#Award badge to user based on posts
def check_post_badges(user_id):
    conn = get_db_connection()
    count = conn.execute(
        'SELECT COUNT(*) FROM post WHERE user_id = ?', (user_id,)).fetchone()[0]
    for milestone in [10, 50, 100]:
        if count >= milestone:
            award_badge_if_eligible(user_id, f'post_{milestone}_post')
    conn.close()

#Award badge to user based on quiz completion
def award_quiz_badge(user_id, level):
    conn = get_db_connection()
    badge = conn.execute('SELECT * FROM badge WHERE criteria = ?', (f'quiz_{level}',)).fetchone()
    if badge:
        already_claimed = conn.execute(
            'SELECT 1 FROM user_badge WHERE user_id = ? AND badge_id = ?', (user_id, badge['id'])
        ).fetchone()
        if not already_claimed:
            conn.execute(
                'INSERT INTO user_badge (user_id, badge_id) VALUES (?, ?)', (user_id, badge['id'])
            )
            conn.commit()
    conn.close()

#Award badge to user based on contest winner
def award_contest_winner_badge(user_id, contest_id):
    criteria = f'contest_winner_{contest_id}'
    award_badge_if_eligible(user_id, criteria)

#Admin manage badges
@badge_bp.route('/admin/badges', methods=['GET', 'POST'])
@login_required
def manage_badges():
    if hasattr(current_user, 'role') and current_user.role == 'admin':
        conn = get_db_connection()
        badges = conn.execute('SELECT * FROM badge').fetchall()
        contests = conn.execute('SELECT id, name FROM contests').fetchall()
        if request.method == 'POST':
            name = request.form['badge_name']
            description = request.form['badge_description']
            criteria = request.form['criteria']
            icon_file = request.files['icon']
            if icon_file and allowed_file(icon_file.filename):
                filename = secure_filename(icon_file.filename)
                icon_path = os.path.join(current_app.static_folder, 'badges', filename)
                os.makedirs(os.path.dirname(icon_path), exist_ok=True)
                icon_file.save(icon_path)
                conn.execute(
                    'INSERT INTO badge (name, description, criteria, icon) VALUES (?, ?, ?, ?)',
                    (name, description, criteria, filename)
                )
                conn.commit()
                flash('Badge added successfully!', 'success')
                conn.close()
                return redirect(url_for('badge.manage_badges'))
            else:
                flash('Invalid file type.', 'error')
        badges = conn.execute('SELECT * FROM badge').fetchall()
        conn.close()
        return render_template('manage_badges.html', badges=badges, contests=contests, user=current_user)
    else:
        flash('You are not authorized to manage badges.', 'error')
        return redirect(url_for('badge.badge_gallery'))

@badge_bp.route('/admin/badges/edit/<int:badge_id>', methods=['GET', 'POST'])
@login_required
def edit_badge(badge_id):
    if hasattr(current_user, 'role') and current_user.role == 'admin':
        conn = get_db_connection()
        badges = conn.execute('SELECT * FROM badge').fetchall()
        contests = conn.execute('SELECT id, name FROM contests').fetchall()
        badge = conn.execute('SELECT * FROM badge WHERE id = ?', (badge_id,)).fetchone()
        if request.method == 'POST':
            name = request.form['badge_name']
            description = request.form['badge_description']
            criteria = request.form['criteria']
            icon_file = request.files.get('icon')
            if icon_file and allowed_file(icon_file.filename):
                filename = secure_filename(icon_file.filename)
                icon_path = os.path.join(current_app.static_folder, 'badges', filename)
                icon_file.save(icon_path)
                conn.execute(
                    'UPDATE badge SET name=?, description=?, criteria=?, icon=? WHERE id=?',
                    (name, description, criteria, filename, badge_id)
                )
            else:
                conn.execute(
                    'UPDATE badge SET name=?, description=?, criteria=? WHERE id=?',
                    (name, description, criteria, badge_id)
                )
            conn.commit()
            flash('Badge updated successfully!', 'success')
            conn.close()
            return redirect(url_for('badge.manage_badges'))
        conn.close()
        return render_template('edit_badge.html', contests=contests, badge=badge, user=current_user)
    else:
        flash('You are not authorized to edit badges.', 'error')
        return redirect(url_for('badge.badge_gallery'))

@badge_bp.route('/admin/badges/delete/<int:badge_id>', methods=['POST'])
@login_required
def delete_badge(badge_id):
    if hasattr(current_user, 'role') and current_user.role == 'admin':
        conn = get_db_connection()
        conn.execute('DELETE FROM badge WHERE id = ?', (badge_id,))
        conn.commit()
        conn.close()
        flash('Badge deleted successfully!', 'success')
        return redirect(url_for('badge.manage_badges'))
    else:
        flash('You are not authorized to delete badges.', 'error')
        return redirect(url_for('badge.badge_gallery'))
import os
import sqlite3
from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'
badge_bp = Blueprint('badge', __name__)

UPLOAD_FOLDER = 'Website/static/badge' #Folder to store uploaded files
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
def badge_gallery():
    if not current_user.is_authenticated:
        flash("You must be logged in to view badge gallery!", category="error")
        return redirect(url_for('auth.login'))
    
    user_role = getattr(current_user, 'role', None)
    conn = get_db_connection()
    badges = conn.execute('SELECT * FROM badge').fetchall()
    user_badges = conn.execute('SELECT badge_id FROM user_badge WHERE user_id = ?', (current_user.id,)).fetchall()
    user_badges_ids = {row['badge_id'] for row in user_badges}
    
    claimable_badge_ids = set()
    claimable_badge_ids.update(check_comment_badges(current_user.id))
    claimable_badge_ids.update(check_like_badges(current_user.id))
    claimable_badge_ids.update(check_post_badges(current_user.id))
    claimable_badge_ids.update(check_quiz_badges(current_user.id))
    claimable_badge_ids.update(check_contest_winner_badges(current_user.id))

    conn.close()
    print("Claimable Badges:", claimable_badge_ids)

    return render_template('badge_gallery.html', user_role=user_role, all_badges=badges, user_badges_ids=user_badges_ids, claimable_badge_ids=claimable_badge_ids, user=current_user)

#Claim badge manually
@badge_bp.route('/claim_badge/<int:badge_id>', methods=['POST'])
@login_required
def claim_badge(badge_id):
    conn = get_db_connection()
    already_claimed = conn.execute(
        'SELECT 1 FROM user_badge WHERE user_id = ? AND badge_id = ?', (current_user.id, badge_id)
    ).fetchone()

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

#Check claimable badges based on like count
def check_like_badges(user_id):
    conn = get_db_connection()
    count = conn.execute(
        'SELECT COUNT(*) FROM likes WHERE user_id = ?', (user_id,)).fetchone()[0]
    claimable_badges = set()

    for milestone in [10, 50, 100, 500]:
        criteria = f'like_{milestone}_posts'
        badge = conn.execute('SELECT * FROM badge WHERE criteria = ?', (criteria,)).fetchone()
        if badge:
            already_claimed = conn.execute(
                'SELECT 1 FROM user_badge WHERE user_id = ? AND badge_id = ?', (user_id, badge['id'])
            ).fetchone()
            if count >= milestone and not already_claimed:
                claimable_badges.add(badge['id'])

    conn.close()
    return claimable_badges

#Check claimable badges based on comment count
def check_comment_badges(user_id):
    conn = get_db_connection()
    count = conn.execute(
        'SELECT COUNT(*) FROM comment WHERE user_id = ?', (user_id,)).fetchone()[0]   
    claimable_badges = set ()

    for milestone in [10, 50, 100, 500]:
        criteria = f'comment_{milestone}'
        badge = conn.execute('SELECT * FROM badge WHERE criteria = ?', (criteria,)).fetchone()
        if badge:
            already_claimed = conn.execute(
                'SELECT 1 FROM user_badge WHERE user_id = ? AND badge_id = ?', (user_id, badge['id'])
            ).fetchone()
            if count >= milestone and not already_claimed:
                claimable_badges.add(badge['id'])

    conn.close()
    return claimable_badges

#Check claimable badges based on post count
def check_post_badges(user_id):
    conn = get_db_connection()
    count = conn.execute(
        'SELECT COUNT(*) FROM post WHERE user_id = ?', (user_id,)).fetchone()[0]
    claimable_badges = set()

    for milestone in [10, 50, 100, 500]:
        criteria = f'upload_{milestone}_posts'
        badge = conn.execute('SELECT * FROM badge WHERE criteria = ?', (criteria,)).fetchone()
        if badge:
            already_claimed = conn.execute(
                'SELECT 1 FROM user_badge WHERE user_id = ? AND badge_id = ?', (user_id, badge['id'])
            ).fetchone()
            if count >= milestone and not already_claimed:
                claimable_badges.add(badge['id'])

    conn.close()
    return claimable_badges

#Check claimable badges based on quiz completion
def check_quiz_badges(user_id):
    conn = get_db_connection()
    claimable_badges = set()

    for level in [1, 2]:  
        criteria = f'quiz_level{level}'
        badge = conn.execute('SELECT * FROM badge WHERE criteria = ?', (criteria,)).fetchone()
        if badge:
            already_claimed = conn.execute(
                'SELECT 1 FROM user_badge WHERE user_id = ? AND badge_id = ?', (user_id, badge['id'])
            ).fetchone()
            user = conn.execute(f'SELECT level{level}_completed FROM user WHERE id = ?', (user_id,)).fetchone()

            if user and user[f'level{level}_completed'] and not already_claimed:
                claimable_badges.add(badge['id'])

    conn.close()
    return claimable_badges

#Check claimable badges based on contest winner
def check_contest_winner_badges(user_id):
    conn = get_db_connection()
    claimable_badges = set()

    badges = conn.execute("SELECT * FROM badge WHERE criteria LIKE 'contest_winner_%'").fetchall()
    for badge in badges:
        contest_id = badge['criteria'].split('_')[-1]
        already_claimed = conn.execute(
            'SELECT 1 FROM user_badge WHERE user_id = ? AND badge_id = ?', (user_id, badge['id'])
        ).fetchone()

        highest_votes_row = conn.execute('SELECT MAX(votes) as max_votes FROM submissions WHERE contest_id = ?', (contest_id,)).fetchone()
        max_votes = highest_votes_row['max_votes'] if highest_votes_row else None

        if max_votes and max_votes > 0: 
            winner_submissions = conn.execute('SELECT name FROM submissions WHERE contest_id = ? AND votes = ?', (contest_id, max_votes)).fetchall()
            winner_names = {row['name'].strip().lower() for row in winner_submissions}

            if current_user.Name.strip().lower() in winner_names and not already_claimed:
                claimable_badges.add(badge['id'])

    conn.close()
    return claimable_badges

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
        return render_template('manage_badges.html', badges=badges, user=current_user, contests=contests)
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
        return render_template('edit_badge.html', badge=badge, user=current_user, badges=badges, contests=contests)
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
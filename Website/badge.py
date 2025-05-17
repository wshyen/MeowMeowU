import os
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

badge_bp = Blueprint('badge', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('datebase.db')  
    conn.row_factory = sqlite3.Row
    return conn

#User badge gallery
@badge_bp.route('/badges')
@login_required
def badge_gallery():
    conn = get_db_connection()
    badges = conn.execute('SELECT * FROM badge').fetchall()
    user_badges = conn.execute('SELECT badge_id FROM user_badge WHERE user_id = ?', (current_user.id,)).fetchall()
    user_badges_ids = {row['badge_id'] for row in user_badges}
    conn.close()
    return render_template('badge_gallery.html', all_badges=badges, user_badges_ids=user_badges_ids)

#Single badge page
@badge_bp.route('/badge/<int:badge_id>')
@login_required
def badge(badge_id):
    conn = get_db_connection()
    badge = conn.execute('SELECT * FROM badge WHERE id = ?', (badge_id,)).fetchone()
    already_claimed = conn.execute(
        'SELECT 1 FROM user_badge WHERE user_id = ? AND badge_id = ?', (current_user.id, badge_id)
    ).fetchone()
    conn.close()
    reason = request.args.get('reason', 'generic')
    return render_template('badge.html', badge=badge, reason=reason, user=current_user, already_claimed=already_claimed)

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
    return redirect(url_for('badge.badge', badge_id=badge_id, reason=reason))

#Admin manage badges
@badge_bp.route('/admin/badges', methods=['GET', 'POST'])
@login_required
def manage_badges():
    if hasattr(current_user, 'role') and current_user.role == 'admin':
        conn = get_db_connection()
        if request.method == 'POST':
            name = request.form['badge_name']
            description = request.form['badge_description']
            criteria = request.form['criteria']
            icon_file = request.files['icon']
            if icon_file and allowed_file(icon_file.filename):
                filename = secure_filename(icon_file.filename)
                icon_path = os.path.join(current_app.static_folder, 'badges', filename)
                icon_file.save(icon_path)
                conn.execute(
                    'INSERT INTO badge (name, description, criteria, icon) VALUES (?, ?, ?, ?)',
                    (name, description, criteria, filename)
                )
                conn.commit()
                flash('Badge added!', 'success')
                conn.close()
                return redirect(url_for('badge.manage_badges'))
            else:
                flash('Invalid file type.', 'error')
        badges = conn.execute('SELECT * FROM badge').fetchall()
        conn.close()
        return render_template('manage_badges.html', badges=badges)
    else:
        flash('You are not authorized to manage badges.', 'error')
        return redirect(url_for('badge.badge_gallery'))

@badge_bp.route('/admin/badges/edit/<int:badge_id>', methods=['GET', 'POST'])
@login_required
def edit_badge(badge_id):
    if hasattr(current_user, 'role') and current_user.role == 'admin':
        conn = get_db_connection()
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
            flash('Badge updated!', 'success')
            conn.close()
            return redirect(url_for('badge.manage_badges'))
        conn.close()
        return render_template('edit_badge.html', badge=badge)
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
        flash('Badge deleted!', 'success')
    else:
        flash('You are not authorized to delete badges.', 'error')
        return redirect(url_for('badge.badge_gallery'))
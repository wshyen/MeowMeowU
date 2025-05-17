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

@badge_bp.route('/badges')
@login_required
def badge_gallery():
    conn = get_db_connection()
    badges = conn.execute('SELECT * FROM badge').fetchall()
    user_badges = conn.execute('SELECT badge_id FROM user_badge WHERE user_id = ?', (current_user.id,)).fetchall()
    user_badges_ids = {row['badge_id'] for row in user_badges}
    conn.close()
    return render_template('badge_gallery.html', all_badges=badges, user_badges_ids=user_badges_ids)

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


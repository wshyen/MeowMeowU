import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Badge, UserBadge

badge_bp = Blueprint('badge', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@badge_bp.route('/badges')
@login_required
def badge_gallery():
    all_badges = Badge.query.all()
    user_badges_ids = {ub.badge_id for ub in UserBadge.query.filter_by(user_id=current_user.id).all()}
    return render_template('badge_gallery.html', all_badges=all_badges, user_badges_ids=user_badges_ids)

@badge_bp.route('/badge/<int:badge_id>')
@login_required
def badge(badge_id):
    badge = Badge.query.get_or_404(badge_id)
    reason = request.args.get('reason', 'generic')
    return render_template('badge.html', badge=badge, reason=reason, user=current_user)
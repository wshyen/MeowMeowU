import os
import sqlite3
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user, login_required
from .models import Note, Story
from .import db

views = Blueprint("views", __name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'datebase.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@views.route("/")
def home():
    latest_stories = Story.query.order_by(Story.created_at.desc()).limit(1).all()

    conn = get_db_connection()
    popular_post = conn.execute('''
        SELECT post.*, 
            (SELECT COUNT(*) FROM likes WHERE likes.post_id = post.post_id) AS like_count
        FROM post
        ORDER BY like_count DESC
        LIMIT 1
    ''').fetchone()
    conn.close()
    return render_template("home.html", user=current_user, stories=latest_stories, popular_post=popular_post)

@views.route('/suggestion-box', methods=['GET', 'POST'])
def suggestion():
    if not current_user.is_authenticated:
        flash("You must be logged in to give suggestion!", category="error")
        return redirect(url_for('auth.login'))
    
    if request.method == "POST":
        note = request.form.get("note")

        if not note or len(note.strip()) == 0:
            flash('Please enter a valid suggestion!', category='error')
        elif len(note.strip()) == 1:
            flash('Suggestion is too short! Please try again.', category='error')
        else:
            new_note = Note(data=note.strip(), user_id=current_user.id)
            db.session.add(new_note)
            db.session.commit()
            flash('Suggestion added!', category='success')
        return redirect(url_for('views.suggestion'))

    notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.id).all()
    index = request.args.get('index', default=0, type=int)

    #clamp index to valid range
    if index < 0:
        index = 0
    elif index >= len(notes):
        index = len(notes) - 1 if notes else 0

    current_note = notes[index] if notes else None

    return render_template("suggestion.html", user=current_user, current_note=current_note, index=index, total=len(notes))

@views.route('/contest_submission', methods=['GET', 'POST'])
@login_required
def contest_submission():
    if request.method == "POST":
        contest_id = request.form.get("contest")
        entry_description = request.form.get("description")
        uploaded_file = request.files.get("file")

        #Ensure logged in user is submitting the entry
        user_id = current_user.id
        username = current_user.username #Auto fetch user's current username

        if contest_id and uploaded_file:
            new_entry = ContestEntry(user_id=user_id, username=username,
                                     contest_id=contest_id, description=entry_description, 
                                     file=uploaded_file.filename)
            db.session.add(new_entry)
            db.session.commit()
        
        return redirect(url_for('views.contest_submission'))

    return render_template("contest_submission.html", user=current_user)

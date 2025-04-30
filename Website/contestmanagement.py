import os
import sqlite3
from flask import Flask, Blueprint, render_template, request, session, redirect, url_for, jsonify, flash
from flask_login import current_user 
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'
contestmanagement_bp = Blueprint('contestmanagement', __name__, template_folder='templates', static_folder='static')

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png','jpg','jpeg'}
app.config['UPLOAD_FOLDER'] = 'static/contest' #Folder to store uploaded files
app.config['SECRET_KEY'] = 'your_secret_key'

def get_db_connection():
    conn = sqlite3.connect('datebase.db')  
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Assuming user validation is correct
        session['user'] = username  # Set the session when the user is logged in
        return redirect(url_for('contestmanagement.contest'))  # Redirect to the profile page
    
    return render_template('login.html')

@contestmanagement_bp.route("/contest_page")
def contest_page():
    return render_template("contest.html", contests=contests, user=current_user)

@contestmanagement_bp.route('/create_contest', methods=['GET', 'POST'])
@login_required 
def create_contest():
    def create_contest():
    conn = get_db_connection()
    user = conn.execute("SELECT role FROM users WHERE username = ?", (current_user.username,)).fetchone()
    conn.close()
    
    if user and user['role'] == 'admin':  
        return render_template('create_contest.html')
    else:
        flash("Access Denied. Admins Only!", "error")
        return redirect(url_for('contestmanagement.contest_page'))

@contestmanagement_bp.route('/contest_submission', methods=['GET', 'POST'])
def submit_contest():
    return render_template("contest_submission.html")

@contestmanagement_bp.route('/contest_submission', methods=['POST'])
def check_user_submission(user_id):
    existing_entry = Submission.query.filter_by(user_id=user_id).first()
    if existing_entry:
        return "You have already submitted an entry."
    else:
        return None

app.register_blueprint(contestmanagement_bp)

if __name__ == '__main__':
    app.run(debug=True)
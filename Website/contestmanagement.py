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
    conn = get_db_connection()
    contests = conn.execute("SELECT * FROM contests").fetchall()  # Get all contests
    conn.close()
    
    return render_template("contest.html", contests=contests, user=current_user)

@contestmanagement_bp.route('/create_contest', methods=['GET', 'POST'])
@login_required 
def create_contest():
    conn = get_db_connection()
    user = conn.execute("SELECT role FROM users WHERE username = ?", (current_user.username,)).fetchone()
    conn.close()

    with get_db_connection() as conn:
    conn.execute('''
        INSERT INTO contests (name, description, start_datetime, end_datetime, voting_start, voting_end, result_announcement, purpose, rules, prizes, banner_url) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (contest_name, description, start_datetime, end_datetime, voting_start, voting_end, result_announcement, purpose, rules, prizes, banner_url))
    conn.commit()  #Save changes

    if user and user['role'] == 'admin':  
        return render_template('create_contest.html')
    else:
        flash("Access Denied. Admins Only!", "error")
        return redirect(url_for('contestmanagement.contest_page'))

@contestmanagement_bp.route('/contest_submission', methods=['GET', 'POST'])
def submit_contest():
    if request.method == 'POST':
        username = request.form['username']
        contest = request.form['contest']
        description = request.form['description']
        file = request.files['file']
        rules_agree = request.form.get('rulesAgree')

       #Validate the file type
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)  #Save the file inside the contest folder
         else:
            flash("Invalid file format! Only JPG, JPEG and PNG are allowed.", "error")
            return redirect(url_for('contestmanagement.submit_contest'))

        #Save the submission to the database
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO submissions (username, contest, description, file_path, rules_agree) 
                VALUES (?, ?, ?, ?, ?)
            ''', (username, contest, description, file_path, rules_agree))
            conn.commit()

        return redirect(url_for('contestmanagement.contest_page'))  # Sends user back to the contest page after submission

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
    #Ensure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    #Creates database table if it doesn't exist
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contests ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                start_datetime TEXT NOT NULL,
                end_datetime TEXT NOT NULL,
                voting_start TEXT NOT NULL,
                voting_end TEXT NOT NULL,
                result_announcement TEXT NOT NULL,
                purpose TEXT NOT NULL,
                rules TEXT NOT NULL,
                prizes TEXT NOT NULL,
                banner_url TEXT
            )
        ''')
        #Create the table if it doesn't exists
        #Name of the table is contests
        #id INTEGER PRIMARY KEY AUTOINCREMENT Adds an id to the table
        #TEXT NOT NULL Adds a column for the name, description, start_datetime, end_datetime, voting_start, voting_end, result_announcement, purpose, rules and prizes which are a must to fill in
        #TEXT Adds a column for the banner_url which is not a must to fill in

        app.run(debug=True)
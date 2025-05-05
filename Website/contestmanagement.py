import os
import sqlite3
from flask import Flask, Blueprint, render_template, request, session, redirect, url_for, jsonify, flash
from flask_login import current_user, login_required, UserMixin, LoginManager, login_user
from werkzeug.utils import secure_filename
from datetime import date

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'
contestmanagement_bp = Blueprint('contestmanagement', __name__, template_folder='templates', static_folder='static')

UPLOAD_FOLDER = 'Website/static/uploads'
ALLOWED_EXTENSIONS = {'png','jpg','jpeg'}
app.config['UPLOAD_FOLDER'] = 'Website/static/contest' #Folder to store uploaded files

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
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL CHECK (role IN ('admin', 'user'))
            )
        ''')
        
        # Check if admins are already inserted
        existing_admins = conn.execute("SELECT * FROM user WHERE role='admin'").fetchall()

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        print(f"DEBUG: login POST hit — email = {email}")

        conn = get_db_connection()
        user = conn.execute('''
            SELECT rowid AS id, email, role
            FROM user
            WHERE email = ?
        ''', (email,)).fetchone()
        conn.close()

        print(f"DEBUG: Raw user query result = {user}") 

        if user:
            user_obj = CustomUser(id=user['id'], email=user['email'], role=user['role'])
            login_user(user_obj)

            print("DEBUG: Logged in user:", user_obj)

            session['role'] = user_obj.role
            session.permanent = True  # Make the session permanent
            session.modified = True  #Mark session as modified to ensure it is saved
            print(f"DEBUG: session role set to {session['role']}")

            return redirect(url_for('contestmanagement.contest_page'))
        else:
            flash("Invalid credentials!", "error")
            return render_template('login.html')

    return render_template('login.html')

@contestmanagement_bp.route("/contest_page")
def contest_page():
    print(f"DEBUG: current_user = {current_user}")  # Debugging current_user 

    user_role = getattr(current_user, 'role', 'user')
    print(f"DEBUG: user_role = {user_role}")

    conn = get_db_connection()
    contests = conn.execute("SELECT * FROM contests").fetchall()  # Get all contests
    conn.close()
    
    return render_template("contest.html", contests=contests, user=current_user, user_role=user_role)

@contestmanagement_bp.route('/create_contest', methods=['GET', 'POST'])
@login_required 
def create_contest():
    print(f"DEBUG: current_user = {current_user}")
    print(f"DEBUG: current_user.__dict__ = {current_user.__dict__}")

    if hasattr(current_user, 'role') and current_user.role == 'admin':
        if request.method == 'POST':
            contest_name = request.form['contest_name']
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            voting_start = request.form['voting_start']
            voting_end = request.form['voting_end']
            result_announcement = request.form['result_announcement']
            purpose = request.form['purpose']
            rules = request.form['rules']
            prizes = request.form['prizes']
            file = request.files['contest_banner']
        
            #Validate and save banner image
            banner_url = None  #Default to None in case no file is uploaded or it's invalid

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)

                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  #Ensure folder exists

                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)  # Save the actual file

                banner_url = f"contest/{filename}"

            with get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO contests (name, start_date, end_date, voting_start, voting_end, result_announcement, purpose, rules, prizes, banner_url) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (contest_name, start_date, end_date, voting_start, voting_end, result_announcement, purpose, rules, prizes, banner_url))
                conn.commit()  #Save changes

            return redirect(url_for('contestmanagement.contest_page'))  #Send admins back to the contest page after creating a contest

        return render_template('create_contest.html', user=current_user) 
    else:
        flash("Access Denied. Admins Only!", "error")
        return redirect(url_for('contestmanagement.contest_page')) #Send non-admins back to the contest page
        
@contestmanagement_bp.route('/contest_submission', methods=['POST'])
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
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
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

def check_user_submission(user_id):
    existing_entry = Submission.query.filter_by(user_id=user_id).first()
    if existing_entry:
        return "You have already submitted an entry."
    else:
        return None

if __name__ == '__main__':
    #Ensure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    initialize_database() 

    #Creates database table if it doesn't exist
    with get_db_connection() as conn:
        admin_emails = ['breannleemy@gmail.com', 'limwanshyen@gmail.com', 'yinniesiew@gmail.com']
        for email in admin_emails:
            conn.execute('''
                INSERT OR IGNORE INTO user (email, role)
                VALUES (?, 'admin')
            ''', (email,))
        conn.commit()

        conn.execute('''
            CREATE TABLE IF NOT EXISTS contests ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
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
        #TEXT NOT NULL Adds a column for the name, start_date, end_date, voting_start, voting_end, result_announcement, purpose, rules and prizes which are a must to fill in
        #TEXT Adds a column for the banner_url which is not a must to fill in

        conn.commit()

    app.run(debug=True)
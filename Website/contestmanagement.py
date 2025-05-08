import os
import sqlite3
from flask import Flask, Blueprint, render_template, request, session, redirect, url_for, jsonify, flash
from flask_login import current_user, login_required, login_user
from werkzeug.utils import secure_filename
from datetime import date, datetime

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
        #Enable Foreign Key Constraints 
        conn.execute("PRAGMA foreign_keys = ON;")  #Stops submissions from referencing non-existent contests.

        conn.execute('''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL CHECK (role IN ('admin', 'user'))
            )
        ''')
        conn.commit()

        conn.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                contest_id INTEGER NOT NULL,
                description TEXT,
                file_path TEXT NOT NULL,
                rules_agree BOOLEAN NOT NULL,
                submission_date DATE DEFAULT DATE('now'),
                FOREIGN KEY (contest_id) REFERENCES contests (id)
            )
        ''')
        conn.commit()

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
    
    today = date.today()

    contests = [dict(c) for c in contests]

    for c in contests:
        c["start_date"] = datetime.strptime(c["start_date"], "%Y-%m-%d").date()  #Convert string to date
        c["end_date"] = datetime.strptime(c["end_date"], "%Y-%m-%d").date()  #Convert string to date

    #Categorize contests based on proper date comparisons
    ongoing_contests = sorted(
        [c for c in contests if c["start_date"] <= today and c["end_date"] >= today], key=lambda x: x["end_date"]
    )  #Sort ongoing contests so those ending soonest are first

    upcoming_contests = sorted(
        [c for c in contests if c["start_date"] > today], key=lambda x: x["start_date"]
    )  #Sort upcoming contests by start date

    completed_contests = sorted(
        [c for c in contests if c["end_date"] < today], key=lambda x: x["end_date"], reverse=True 
    )  #Sort completed contests with the latest ended at the top
    
    return render_template("contest.html", contests=contests, user=current_user, user_role=user_role, user_has_submitted=user_has_submitted, ongoing_contests=ongoing_contests, upcoming_contests=upcoming_contests, completed_contests=completed_contests)

@contestmanagement_bp.route('/create_contest', methods=['GET', 'POST'])
@login_required 
def create_contest():
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
        
            if not file or file.filename == '':
                flash("Banner is required to create a contest!", "error")
                return redirect(url_for('contestmanagement.create_contest'))

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  #Ensure folder exists
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_path = file_path.replace("\\", "/")  #Convert backslashes to forward slashes
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
        
@contestmanagement_bp.route('/contest_submission/<int:contest_id>', methods=['GET', 'POST'])
@login_required
def submit_contest(contest_id):
    conn = get_db_connection()
    contest = conn.execute("SELECT id, name FROM contests WHERE id = ?", (contest_id,)).fetchone()
    if contest is None:
        flash("Invalid contest. You cannot submit an entry.", "error")
        return redirect(url_for('contestmanagement.contest_page'))
    
    if user_has_submitted(current_user.UserName, contest_id):
        flash("You have already submitted an entry for this contest.", "error")
        return redirect(url_for('contestmanagement.contest_page'))

    if request.method == 'POST':
        print("Received Form Data:", request.form)  #Debugging 
        description = request.form['description']
        file = request.files['file']
        rules_agree = bool(request.form.get('rulesAgree')) #Convert to boolean

       #Validate the file type
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_path = file_path.replace("\\", "/")  #Convert backslashes to forward slashes
                file.save(file_path)  #Save the file inside the contest folder
            except Exception as e:
                flash(f"Error saving file: {e}", "error")
                return redirect(url_for('contestmanagement.submit_contest', contest_id=contest_id))
        else:
            flash("Invalid file format! Only JPG, JPEG and PNG are allowed.", "error")
            return redirect(url_for('contestmanagement.submit_contest', contest_id=contest_id))

        #Save the submission to the database
        with get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO submissions (username, contest_id, description, file_path, rules_agree) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (current_user.UserName, contest_id, description, file_path, rules_agree))
                conn.commit() #Save changes

        return redirect(url_for('contestmanagement.contest_page'))  #Sends user back to the contest page after submission

    return render_template("contest_submission.html", contest_id=contest_id, user=current_user, contest=contest)

def user_has_submitted(username, contest_id):
    if not username or not contest_id:
        return False

    conn = get_db_connection()
    existing_entry = conn.execute(
        "SELECT * FROM submissions WHERE username = ? AND contest_id = ?",
        (username, contest_id)
    ).fetchone()
    conn.close()

    return existing_entry is not None

if __name__ == '__main__':
    #Ensure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    initialize_database() 

    #Creates database table if it doesn't exist
    with get_db_connection() as conn:
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
                banner_url TEXT NOT NULL
            )
        ''')
        #Create the table if it doesn't exists
        #Name of the table is contests
        #id INTEGER PRIMARY KEY AUTOINCREMENT Adds an id to the table
        #TEXT NOT NULL Adds a column for the banner, name, start_date, end_date, voting_start, voting_end, result_announcement, purpose, rules and prizes which are a must to fill in

        conn.commit()

    app.run(debug=True)

@contestmanagement_bp.route("/voting", methods=["GET", "POST"])
@login_required
def voting():
    return render_template("voting.html", user=current_user)
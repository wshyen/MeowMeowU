import os
import sqlite3
from flask import Flask, Blueprint, render_template, request, session, redirect, url_for, jsonify, flash
from flask_login import current_user, login_required, login_user
from werkzeug.utils import secure_filename
from datetime import date, datetime

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'
contestmanagement_bp = Blueprint('contestmanagement', __name__, template_folder='templates', static_folder='static')

UPLOAD_FOLDER = 'Website/static/contest' #Folder to store uploaded files
ALLOWED_EXTENSIONS = {'png','jpg','jpeg'}
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
        #Enable Foreign Key Constraints 
        conn.execute("PRAGMA foreign_keys = ON;")  #Stops submissions from referencing non-existent contests

        conn.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contest_id INTEGER NOT NULL,
                description TEXT,
                file_path TEXT NOT NULL,
                rules_agree BOOLEAN NOT NULL,
                submission_date DATE DEFAULT DATE('now'),
                FOREIGN KEY (contest_id) REFERENCES contests (id)
            )
        ''')
        conn.commit()

        #Check if admins are already inserted
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
            session.permanent = True  #Make the session permanent
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
        c["voting_end"] = datetime.strptime(c["voting_end"], "%Y-%m-%d").date()

    #Categorize contests based on proper date comparisons
    ongoing_contests = sorted(
        [c for c in contests if c["start_date"] <= today and c["voting_end"] >= today], key=lambda x: x["voting_end"]
    )  #Sort ongoing contests so those ending soonest are first

    upcoming_contests = sorted(
        [c for c in contests if c["start_date"] > today], key=lambda x: x["start_date"]
    )  #Sort upcoming contests by start date

    completed_contests = sorted(
        [c for c in contests if c["voting_end"] < today], key=lambda x: x["voting_end"], reverse=True 
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
    
    if user_has_submitted(current_user.Name, contest_id):
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
                    INSERT INTO submissions (name, contest_id, description, file_path, rules_agree) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (current_user.Name, contest_id, description, file_path, rules_agree))
                conn.commit() #Save changes

        return redirect(url_for('contestmanagement.contest_page'))  #Sends user back to the contest page after submission

    return render_template("contest_submission.html", contest_id=contest_id, user=current_user, contest=contest)

def user_has_submitted(name, contest_id):
    if not name or not contest_id:
        return False

    conn = get_db_connection()
    existing_entry = conn.execute(
        "SELECT * FROM submissions WHERE name = ? AND contest_id = ?",
        (name, contest_id)
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

#voting system
@contestmanagement_bp.route('/voting/<int:contest_id>', methods=['GET', 'POST'])
def voting(contest_id):
    conn = get_db_connection()

    contest = conn.execute("SELECT name, voting_start, voting_end FROM contests WHERE id = ?", (contest_id,)).fetchone()
    if not contest:
        flash("Contest not found!", "error")
        return redirect(url_for('contestmanagement.contest_page'))

    contest_name = contest["name"]

    #ensure voting times have full date-time format
    voting_start_str = contest["voting_start"]
    voting_end_str = contest["voting_end"]

    if len(voting_start_str) == 10:  #if stored as "YYYY-MM-DD"
        voting_start_str += " 00:00:00"  #add default time
    if len(voting_end_str) == 10:  #if stored as "YYYY-MM-DD"
        voting_end_str += " 23:59:59"  #add end-of-day time

    #convert to datetime format
    voting_start = datetime.strptime(voting_start_str, "%Y-%m-%d %H:%M:%S")
    voting_end = datetime.strptime(voting_end_str, "%Y-%m-%d %H:%M:%S")

    current_time = datetime.now()

    #redirect to countdown page if voting hasn't started yet
    if current_time < voting_start:
        time_left = voting_start - current_time
        days_left = time_left.days
        hours_left = time_left.seconds // 3600
        return render_template("voting_countdown.html", contest_name=contest_name, days_left=days_left, hours_left=hours_left, user=current_user)

    #redirect to contest page if voting has ended
    if current_time > voting_end:
        flash("Voting has ended!", "error")
        return redirect(url_for('contestmanagement.contest_page'))

    participants = conn.execute("SELECT id, name, file_path, votes, description FROM submissions WHERE contest_id = ?", (contest_id,)).fetchall()
    conn.close()

    return render_template("voting.html", contest_name=contest_name, contest_id=contest_id, participants=participants, user=current_user)

@contestmanagement_bp.route('/submit_vote/<int:contest_id>', methods=['POST'])
def submit_vote(contest_id):
    selected_participant_id = request.form.get("vote")

    if not selected_participant_id:
        flash("Please select a participant to vote!", "error")
        return redirect(url_for('contestmanagement.voting', contest_id=contest_id))

    conn = get_db_connection()

    #ensure valid participant
    participant = conn.execute("SELECT id FROM submissions WHERE id = ? AND contest_id = ?", (selected_participant_id, contest_id)).fetchone()
    if not participant:
        flash("Invalid participant!", "error")
        return redirect(url_for('contestmanagement.voting', contest_id=contest_id))

    #check if user has already voted
    user_id = current_user.id 
    has_voted = conn.execute("SELECT id FROM votes WHERE user_id = ? AND contest_id = ?", (user_id, contest_id)).fetchone()

    if has_voted:
        flash("You have already voted in this contest!", "error")
        return redirect(url_for('contestmanagement.voting', contest_id=contest_id))

    #add vote to db
    conn.execute("INSERT INTO votes (user_id, contest_id, participant_id) VALUES (?, ?, ?)", (user_id, contest_id, selected_participant_id))

    #update votes count
    conn.execute("UPDATE submissions SET votes = COALESCE(votes, 0) + 1 WHERE id = ?", (selected_participant_id,))
    conn.commit()
    conn.close()

    flash("Your vote has been recorded!", "success")
    return redirect(url_for('contestmanagement.voting', contest_id=contest_id))

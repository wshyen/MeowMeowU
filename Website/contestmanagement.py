from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  

@app.route("/")
def contest_page():
    return render_template("contest.html", contests=contests, user=current_user)

@app.route('/create_contest', methods=['GET', 'POST'])
def create_contest():
    if current_user.role != 'admin':  #Check if user is an admin
        flash("Access Denied. Admins Only!", "error")
        return redirect(url_for('home'))  #Send non-admins users to homepage
    return render_template('create_contest.html')

def check_user_submission(user_id):
    existing_entry = Submission.query.filter_by(user_id=user_id).first()
    if existing_entry:
        return "You have already submitted an entry."
    else:
        return None

if __name__ == '__main__':
    app.run(debug=True)
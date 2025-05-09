import os
import sqlite3
from flask import Flask, Blueprint, render_template, request, session, redirect, url_for, jsonify, flash
from flask_login import current_user, login_required, login_user

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'
quiz_bp = Blueprint('quiz', __name__, template_folder='templates', static_folder='static')

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'datebase.db')
    db_path = os.path.abspath(db_path) 
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn    

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

            return redirect(url_for('quiz.quiz_page'))
        else:
            flash("Invalid credentials!", "error")
            return render_template('login.html')

    return render_template('login.html')

@quiz_bp.route('/quiz', methods=['GET', 'POST'])
def quiz_page():
    print(f"DEBUG: current_user = {current_user}")  #Debugging current_user 

    user_role = getattr(current_user, 'role', 'user')
    print(f"DEBUG: user_role = {user_role}")

@quiz_bp.route('/manage-quiz', methods=['GET'])
@login_required
def manage_quiz():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash("Access denied! You must be an admin to manage quiz questions.", "error")
        return redirect(url_for('quiz.quiz_page'))
        
    conn = get_db_connection()
    questions = conn.execute("SELECT * FROM quiz_questions").fetchall()
    conn.close()

    return render_template('manage_quiz_questions.html', questions=questions)

@quiz_bp.route('/add-question', methods=['POST'])
@login_required
def add_question():
    question = request.form['question']
    option_a = request.form['option_a']
    option_b = request.form['option_b']
    option_c = request.form['option_c']
    correct_option = request.form['correct_option']
    level = request.form['level']

    conn = get_db_connection()
    conn.execute("INSERT INTO quiz_questions (question, option_a, option_b, option_c, correct_option, level) VALUES (?, ?, ?, ?, ?, ?)",
                 (question, option_a, option_b, option_c, correct_option, level))
    conn.commit()
    conn.close()

    flash("Question added successfully!", "success")
    return redirect(url_for('quiz.manage_quiz'))

@quiz_bp.route('/edit-question/<int:question_id>', methods=['POST'])
@login_required
def edit_question(question_id):
    new_text = request.form['new_text']
    option_a = request.form['option_a']
    option_b = request.form['option_b']
    option_c = request.form['option_c']
    correct_option = request.form['correct_option']

    conn = get_db_connection()
    conn.execute("UPDATE quiz_questions SET question = ?, option_a = ?, option_b = ?, option_c = ?, correct_option = ? WHERE id = ?",
                 (new_text, option_a, option_b, option_c, correct_option, question_id))
    conn.commit()
    conn.close()

    flash("Question updated successfully!", "success")
    return redirect(url_for('quiz.manage_quiz'))

@quiz_bp.route('/delete-question/<int:question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT level FROM quiz_questions WHERE id = ?", (question_id,)) #Find the level of question being deleted
    level_result = cursor.fetchone()

    if not level_result:
        flash("Question not found!", "error")
        return redirect(url_for('quiz.manage_quiz'))
    
    level = level_result[0]

    #Count total questions for the specific level
    cursor.execute("SELECT COUNT(*) FROM quiz_questions WHERE level = ?", (level,))
    total_questions = cursor.fetchone()[0]

    if total_questions <= 10:
        flash(f"You must have at least 10 questions in Level {level}! Cannot delete.", "error")
        return redirect(url_for('quiz.manage_quiz'))

    cursor.execute("DELETE FROM quiz_questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()

    flash("Question deleted successfully!", "success")
    return redirect(url_for('quiz.manage_quiz'))

if __name__ == '__main__':
    app.run(debug=True)
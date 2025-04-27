from flask import Flask, render_templates, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'your_secret_key'  

@app.route('/create_contest', methods=['GET', 'POST'])
def create_contest():
    if request.method == 'POST':
        # Store form data in session
        session['contest_name'] = request.form.get('contest_name', '')
        session['start_datetime'] = request.form.get('start_datetime', '')
        session['end_datetime'] = request.form.get('end_datetime', '')
        session['voting_start'] = request.form.get('voting_start', '')
        session['voting_end'] = request.form.get('voting_end', '')
        session['result_announcement'] = request.form.get('result_announcement', '')
        session['purpose'] = request.form.get('purpose', '')
        session['rules'] = request.form.get('rules', '')
        session['prizes'] = request.form.get('prizes', '')

        return redirect(url_for('contest_preview')) #Redirects to Preview Page

    return render_template('create_contest.html', session)
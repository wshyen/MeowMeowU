import os
import sqlite3 #Connect to SQLite database to store and retrieve cat profile infromation
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename #Helps secure file uploads, preventing unsafe filenames that can cause errors or security issues

app = Flask(__name__) 
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png','jpg','jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/login', methods=['GET', 'POST'])
def login():  
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        #Validate username and password from the database
        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                            (username, password)).fetchone()

        if user:
            session['user'] = username  #Set the session to the logged-in username
            print(f"DEBUG: User {username} logged in.")  #Debugging log
            flash("Login successful!", "success")
            return redirect(url_for('view_profiles'))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/simulate_login')
def simulate_login():
    session['user'] = 'test_user'  #Simulate a logged-in user
    print(f"DEBUG: Simulated login as {session['user']}")  #Debugging log
    flash("Simulated login successful! You are logged in as test_user.", "success")
    return redirect(url_for('view_profiles'))  #Redirect to view profiles page

def get_db_connection():
    conn = sqlite3.connect('cat_profiles.db')  #Creates a connection to the database cat_profiles.db
    conn.execute('PRAGMA journal_mode=WAL;')  #Activates Write-Ahead Logging (WAL) in SQLite, enabling simultaneous database reads while a process is writing, improving efficiency and synchronization
    conn.row_factory = sqlite3.Row  #Access rows as dictionaries
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS #Verify if the file is in the allowed list

@app.before_request
def set_current_user():
    session['user'] = session.get('user', None) #Default to None if no user is logged in

@app.route('/profiles')
def view_profiles(): #View all cat profiles
    with get_db_connection() as conn: #Connect to the database to fetch data
        profiles = conn.execute('SELECT * FROM profiles').fetchall() #Get all cat profiles from the database

    profiles = [dict(profile) for profile in profiles] #Convert sqlite3.Row to dictionary

    for profile in profiles:
        if profile['photo'] and profile['photo'] != '':
            profile['photo'] = f"uploads/{profile['photo']}" 
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(profile['photo']))
            if not os.path.exists(full_path):  # Check if the file exists
                profile['photo'] = "uploads/default.png"
        else:
            profile['photo'] = "uploads/default.png"  # Use a default placeholder image
    
    print(f"DEBUG: Profile photo paths = {[profile['photo'] for profile in profiles]}")  #Debugging log
    return render_template('viewprofile.html', profiles=profiles, current_user=session.get('user'))

@app.route('/profiles/create', methods=['GET', 'POST'])
def create_profile():
    if not session.get('user'): #Ensure only logged in users can create profile
        flash("You must be logged in to create a profile. Please log in.", "error")
        return redirect(url_for('simulate_login')) #Sends user back to login page

    if request.method == 'GET': 
        return render_template('createprofile.html')
    
    #Create a new cat profile
    if request.method == 'POST':
        name = request.form['name'].strip().capitalize()
        gender = request.form['gender']
        color = request.form['color']
        description = request.form.get('description', '')  #Optional description
        photo = None

        #Check for duplicate names
        with get_db_connection() as conn:
            existing_names = conn.execute(
                'SELECT name FROM profiles WHERE LOWER(name) = ?',
                (name.lower(),)
            ).fetchone()

        if existing_names:
            flash(f'The name "{name}" is already in use. Please choose a different one.', 'error')
            return redirect(url_for('create_profile')) #Sends user back to the create profile page   

        #Validate required fields
        if not name or not gender or not color:
            flash('Name, gender and color are required!', 'error')
            return redirect(url_for('create_profile')) #Sends user back to the create profile page

        #Validate and save the file
        if 'profile_picture' not in request.files or request.files['profile_picture'].filename == '':
            flash('A profile picture is required!', 'error')
            return redirect(url_for('create_profile')) #Sends user back to the create profile page

        file = request.files['profile_picture']
        if file.content_length is None or file.content_length > 2 * 1024 * 1024:
            flash("File size is too large. Please upload an image under 2MB.", "error") #Display error message to user if file size too big
            return redirect(url_for('create_profile')) #Sends user back to the create profile page

        if not allowed_file(file.filename): #Checks if the file was uploaded in the correct format (png,jpg,jpeg)
            flash('Invalid file format. Please upload a PNG, JPG, or JPEG image.', 'error')
            return redirect(url_for('create_profile')) #Sends user back to the create profile page
            
        try: 
            secure_file = secure_filename(file.filename)
            filename = f"{name.lower()}_{secure_file}" 
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath) 
            photo = filename
        except Exception as e:
            flash(f"An error occurred while saving the file: {str(e)}", "error")
            return redirect(url_for('create_profile'))

        #Insert the new profile into the database
        try:
            creator = session.get('user')
            if not creator:  # Handle missing session key gracefully
                flash("An error occurred while creating the profile. Please log in again.", "error")
                return redirect(url_for('login'))

            print(f"DEBUG: session['user'] = {creator}")
            
            with get_db_connection() as conn:
                conn.execute( 
                    'INSERT INTO profiles (name, gender, color, description, photo, creator) VALUES (?, ?, ?, ?, ?, ?)',
                    (name, gender, color, description, photo, creator) #Automatically assign the logged in user as the creator
                )
                conn.commit() #Save changes to the database
            flash('Cat Profile created successfully!', 'success')
            return redirect(url_for('view_profiles')) #Sends user back to profile list page

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):  #Handle database locked error
                flash("Database is currently busy. Please try again later.", "error")
            else:
                flash("An unexpected error occurred while creating the profile.", "error")
            return redirect(url_for('create_profile')) #Sends user back to the profile list page

    return render_template('createprofile.html')

@app.route('/profiles/<int:id>/edit', methods=['GET', 'POST'])
def edit_profile(id):
    if not session.get('user'): #Ensure only logged in users can create profile
        flash("You must be logged in to edit a profile. Please log in", "error")
        return redirect(url_for('simulate_login')) #Sends user back to login page

    with get_db_connection() as conn: #Connect to the database to retrieve the profile information
        profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (id,)).fetchone() #Get the cat profile with the matching ID

    if not profile:
        flash('Cat Profile not found.', 'error') #Display error message to user if no profile is found
        return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    profile = dict(profile)  # Convert sqlite3.Row to dictionary
    if not profile['photo']:  # Provide a fallback if photo is missing
        profile['photo'] = "uploads/default.png"  # Use a default placeholder image
    else:
        profile['photo'] = f"uploads/{profile['photo']}"  # Ensure the path includes 'uploads'

    if request.method == 'POST':
        if 'remove_picture' in request.form:
            #Check if the user has removed the picture but hasn't uploaded a new one
            if 'profile_picture' not in request.files or request.files['profile_picture'].filename == '':
                flash("You must upload a new profile picture before saving changes.", "error")
                return redirect(url_for('edit_profile', id=id))  #Prevent submission and reload the edit page
            
            with get_db_connection() as conn:
                conn.execute(
                    'UPDATE profiles SET gender = ?, color = ?, description = ?, photo = ? WHERE id = ?',
                    (gender, color, description, photo, id)  #Ensure all fields are updated
                )
                conn.commit()

            flash('Profile picture removed successfully!', 'success')
            return redirect(url_for('edit_profile', id=id)) #Send user back to edit profile page

        name = request.form.get('name', profile['name']).strip().capitalize()
        gender = request.form['gender']
        color = request.form['color']
        description = request.form.get('description', '')
        photo = profile['photo']

        #Validate required fields
        if not name or not gender or not color:
            flash('Name, gender, and color are required!', 'error')
            return redirect(url_for('edit_profile', id=id))

        #Handle file upload 
        if 'profile_picture' in request.files and request.files['profile_picture'].filename != '':
            file = request.files['profile_picture']
            if file.content_length is None or file.content_length > 2 * 1024 * 1024: 
                flash("File size is too large. Please upload an image under 2MB.", "error") #Display error message to user if file size too big
                return redirect(url_for('edit_profile', id=id)) #Sends user back to the edit profile page

            if allowed_file(file.filename):
                secure_file = secure_filename(file.filename)
                filename = f"{profile['name'].lower()}_{profile['id']}.{file.filename.rsplit('.', 1)[1].lower()}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(filepath)
                    photo = filename  #Store only the filename
                except Exception as e:
                    flash(f"An error occurred while saving the file: {str(e)}", 'error')
                    return redirect(url_for('edit_profile', id=id))
        else:
            photo = profile['photo']

        with get_db_connection() as conn:
            conn.execute(
                'UPDATE profiles SET gender = ?, color = ?, description = ?, photo = ? WHERE id = ?',
                (gender, color, description, photo, id)  # Ensure all fields are updated
                )
            conn.commit()

        flash('Profile updated successfully!', 'success') #Notify user profile updated successfully
        return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    return render_template('editprofile.html', profile=profile)

@app.route('/profiles/remove_picture/<int:id>', methods=['POST'])
def remove_profile_picture(id):
    with get_db_connection() as conn:
        profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (id,)).fetchone()

    if not profile:
        flash('Profile not found.', 'error')
        return redirect(url_for('view_profiles'))  #Sends user back to the profile list page

    if profile['photo'] and profile['photo'] != "default.png":
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], profile['photo'])
        if os.path.exists(full_path):
            os.remove(full_path)  #Delete the file from storage

    with get_db_connection() as conn:
        conn.execute('UPDATE profiles SET photo = ? WHERE id = ?', ('',id,))
        conn.commit()

    flash('Profile picture removed successfully!', 'success')
    return redirect(url_for('view_profiles'))  #Sends user back to the profile list page

@app.route('/profiles/<int:id>/delete', methods=['POST'])
def delete_profile(id):
    if not session.get('user'): #Ensure only logged in users can create profile
        flash("You must be logged in to create a profile.", "error")
        return redirect(url_for('view_profiles')) #Sends user back to profile list page

    with get_db_connection() as conn:
        profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (id,)).fetchone()

    if not profile:
        flash('Profile not found.', 'error')
        return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    #Check if the current user is the creator of the profile
    if profile['creator'] != session['user']:
        flash("You are not authorized to delete this profile.", "error")
        return redirect(url_for('view_profiles'))  # Sends user back to the profile list page

    if profile['photo'] and os.path.exists(profile['photo']): #Delete the photo from the filesystem if it exists
        os.remove(profile['photo'])

    with get_db_connection() as conn:
        conn.execute('DELETE FROM profiles WHERE id = ?', (id,))
        conn.commit()

    flash(f'Profile for "{profile["name"]}" has been deleted.', 'success')
    return redirect(url_for('view_profiles')) #Sends user back to the profile list page

@app.route('/profiles/<int:id>/confirm_delete')
def confirm_delete(id):
    with get_db_connection() as conn:
        profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (id,)).fetchone()

    if not profile:
        flash('Profile not found.', 'error') 
        return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    #Check if the current user is the creator of the profile
    if session.get('user') is None or profile['creator'] != session['user']:
        flash('You are not authorized to delete this profile.', 'error')
        return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    if profile['photo']:
        profile = dict(profile)  
        profile['photo'] = f"uploads/{profile['photo']}" 

    return render_template('confirmdelete.html', profile=profile)

if __name__ == '__main__':
    #Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    #Creates database table if it doesn't exist
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS profiles ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                gender TEXT NOT NULL,
                color TEXT NOT NULL,
                description TEXT,
                photo TEXT NOT NULL,
                creator TEXT NOT NULL
            )
        ''')
    #Create the table if it doesn't exists
    #Name of the table is profiles
    #id INTEGER PRIMARY KEY AUTOINCREMENT Adds a unique id for each entry
    #TEXT NOT NULL Adds a column for the name, gender ,color and profile picture which is a must to fill im
    #TEXT Adds a column for description which is not a must to fill in
    #creator TEXT NOT NULL Adds a column for creator which will be automatically filled in by the system 
    conn.close()

    app.run(debug=True)
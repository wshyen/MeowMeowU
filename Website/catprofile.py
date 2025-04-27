import os
import sqlite3 #Connect to SQLite database to store and retrieve cat profile infromation
from flask import Flask, render_template, request, redirect, url_for, flash, session, Blueprint
#Flask to build web app, request to read data sent by users
#Redirect to send users to a different page, flash to show quick messages, session to remember things about users
from flask_login import current_user #To manage user sessions and authentication
from werkzeug.utils import secure_filename #Helps secure file uploads, preventing unsafe filenames that can cause errors or security issues

app = Flask(__name__, static_folder='static') #Flask app to serve static files
app.secret_key = 'your_secret_key' #keeps messages and user data safe
catprofile_bp = Blueprint('catprofile', __name__, template_folder='templates', static_folder='static')

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png','jpg','jpeg'}
app.config['UPLOAD_FOLDER'] = 'static/uploads' #Folder to store uploaded files
app.config['SECRET_KEY'] = 'your_secret_key'  #Ensures session persistence

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Assuming user validation is correct
        session['user'] = username  # Set the session when the user is logged in
        return redirect(url_for('catprofile.view_profiles'))  # Redirect to the profile page
    
    return render_template('login.html')

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'cat_profiles.db')
    conn = sqlite3.connect(db_path)  #Creates a connection to the database cat_profiles.db
    conn.execute('PRAGMA journal_mode=WAL;')  #Activates Write-Ahead Logging (WAL) in SQLite, enabling simultaneous database reads while a process is writing, improving efficiency and synchronization
    conn.row_factory = sqlite3.Row  #Access rows as dictionaries
    return conn

@app.before_request
def set_current_user():
    session['user'] = session.get('user', None) #Default to None if no user is logged in

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS #Verify if the file is in the allowed list

@catprofile_bp.route('/view_profiles')
def view_profiles(): #View all cat profiles
    with get_db_connection() as conn: #Connect to the database to fetch data
        profiles = conn.execute('SELECT * FROM profiles').fetchall() #Get all cat profiles from the database

    profiles = [dict(profile) for profile in profiles] #Convert sqlite3.Row to dictionary

    for profile in profiles:
        if profile['photo'] and profile['photo'] != '':
            profile['photo'] = url_for('static', filename=f'uploads/{profile["photo"]}') 
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(profile['photo']))
            if not os.path.exists(full_path):  #Check if the file exists
                profile['photo'] = "uploads/default.png"
        else:
            profile['photo'] = "uploads/default.png"  #Use a default placeholder image
    
    return render_template('viewprofile.html', profiles=profiles, user=current_user)

@catprofile_bp.route('/profiles/create', methods=['GET', 'POST'])
def create_profile():
    if not session.get('user'): #Ensure only logged in users can create profile
        flash("You must be logged in to create a profile. Please log in.", "error")
        return redirect(url_for('auth.login')) #Sends user back to login page 

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
            all_names = conn.execute('SELECT name FROM profiles').fetchall() #Retrieve all names from 'profiles' table
            print("DEBUG: All names in DB", all_names)

            existing_names = conn.execute(
                'SELECT name FROM profiles WHERE TRIM(LOWER(name)) = ?', #Finds a matching name after trimming spaces & making it lowercase
                (name.lower().strip(),) #Format input name into lowercase and remove extra spaces
            ).fetchone()

        if existing_names:
            flash(f'The name "{name}" is already in use. Please choose a different one.', 'error')
            return redirect(url_for('catprofile.create_profile')) #Sends user back to the create profile page   

        #Validate required fields
        if not name or not gender or not color:
            flash('Name, gender and color are required!', 'error')
            return redirect(url_for('catprofile.create_profile')) #Sends user back to the create profile page

        #Validate and save the file
        if 'profile_picture' not in request.files or request.files['profile_picture'].filename == '':
            flash('A profile picture is required!', 'error')
            return redirect(url_for('catprofile.create_profile')) #Sends user back to the create profile page

        file = request.files['profile_picture']
        if file.content_length is None or file.content_length > 2 * 1024 * 1024:
            flash("File size is too large. Please upload an image under 2MB.", "error") #Display error message to user if file size too big
            return redirect(url_for('catprofile.create_profile')) #Sends user back to the create profile page

        if not allowed_file(file.filename): #Checks if the file was uploaded in the correct format (png,jpg,jpeg)
            flash('Invalid file format. Please upload a PNG, JPG, or JPEG image.', 'error')
            return redirect(url_for('catprofile.create_profile')) #Sends user back to the create profile page
            
        try: 
            secure_file = secure_filename(file.filename)
            filename = f"{name.lower()}_{secure_file}" 
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath) 
            photo = filename
        except Exception as e:
            flash(f"An error occurred while saving the file: {str(e)}", "error")
            return redirect(url_for('catprofile.create_profile'))

        #Insert the new profile into the database
        try:
            creator = session.get('user')
            if not creator:  # Handle missing session key gracefully
                flash("An error occurred while creating the profile. Please log in again.", "error")
                return redirect(url_for('auth.login'))

            print(f"DEBUG: session['user'] = {creator}")
            
            with get_db_connection() as conn:
                conn.execute( 
                    'INSERT INTO profiles (name, gender, color, description, photo, creator) VALUES (?, ?, ?, ?, ?, ?)',
                    (name, gender, color, description, photo, creator) #Automatically assign the logged in user as the creator
                )
                conn.commit() #Save changes to the database
            flash('Cat Profile created successfully!', 'success')
            return redirect(url_for('catprofile.view_profiles')) #Sends user back to profile list page

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):  #Handle database locked error
                flash("Database is currently busy. Please try again later.", "error")
            else:
                flash("An unexpected error occurred while creating the profile.", "error")
            return redirect(url_for('catprofile.create_profile')) #Sends user back to the profile list page

    return render_template('createprofile.html')

@catprofile_bp.route('/profiles/<int:id>/edit', methods=['GET', 'POST'])
def edit_profile(id):
    if not session.get('user'): #Ensure only logged in users can edit profile
        flash("You must be logged in to edit a profile. Please log in.", "error")
        return redirect(url_for('auth.login')) #Sends user back to login page 

    with get_db_connection() as conn: #Connect to the database to retrieve the profile information
        profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (id,)).fetchone() #Get the cat profile with the matching ID

    if not profile:
        flash('Cat Profile not found.', 'error') #Display error message to user if no profile is found
        return redirect(url_for('catprofile.view_profiles')) #Sends user back to the profile list page

    profile = dict(profile)  #Convert sqlite3.Row to dictionary
    if not profile['photo']:  #Provide a fallback if photo is missing
        photo_display = "uploads/default.png"  #Use a default placeholder image
    else:
        photo_display = f"uploads/{profile['photo']}"  #Ensure the path includes 'uploads'

    if request.method == 'POST':
        name = request.form.get('name', profile['name']).strip().capitalize()
        gender = request.form['gender']
        color = request.form['color']
        description = request.form.get('description', '')
        photo = profile['photo']  #Default to the existing photo

        #Validate required fields
        if not name or not gender or not color:
            flash('Name, gender, and color are required!', 'error')
            return redirect(url_for('catprofile.edit_profile', id=id))

        #Handle picture removal
        if 'remove_picture' in request.form:
            #Check if the user has removed the picture but hasn't uploaded a new one
            if 'profile_picture' not in request.files or request.files['profile_picture'].filename == '':
                flash("You must upload a new profile picture before saving changes.", "error")
                return redirect(url_for('catprofile.edit_profile', id=id))  #Prevent submission and reload the edit page
            
            if profile['photo'] and profile['photo'] != "uploads/default.png":
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(profile['photo']))
                if os.path.exists(full_path):
                    os.remove(full_path)  #Remove the file from the filesystem
            photo = "uploads/default.png"  #Update to default placeholder

        #Handle file upload
        elif 'profile_picture' in request.files and request.files['profile_picture'].filename != '':
            file = request.files['profile_picture']
            if file.content_length is None or file.content_length > 2 * 1024 * 1024:
                flash("File size is too large. Please upload an image under 2MB.", "error")
                return redirect(url_for('catprofile.edit_profile', id=id))  #Prevent submission and reload the edit page

            if allowed_file(file.filename):
                secure_file = secure_filename(file.filename)
                filename = f"{name.lower()}_{profile['id']}.{file.filename.rsplit('.', 1)[1].lower()}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(filepath)
                    photo = filename  #Store only the filename
                except Exception as e:
                    flash(f"An error occurred while saving the file: {str(e)}", 'error')
                    return redirect(url_for('catprofile.edit_profile', id=id))
        else:
            photo = profile['photo'] #Keep the old profile picture if no new one is uploaded

        with get_db_connection() as conn:
            conn.execute(
                'UPDATE profiles SET gender = ?, color = ?, description = ?, photo = ? WHERE id = ?',
                (gender, color, description, photo, id)  #Ensure all fields are updated
            )
            conn.commit()

        flash('Profile updated successfully!', 'success') #Notify user profile updated successfully
        return redirect(url_for('catprofile.view_profiles', id=id)) #Sends user back to the profile list page

    return render_template('editprofile.html', profile=profile, photo_display=photo_display)

@catprofile_bp.route('/profiles/remove_picture/<int:id>', methods=['POST'])
def remove_profile_picture(id):
    if not session.get('user'): #Ensure only logged in users can remove profile picture of a profile
        flash("You must be logged in to remove profile picture of a profile. Please log in.", "error")
        return redirect(url_for('auth.login')) #Sends user back to login page 

    with get_db_connection() as conn:
        profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (id,)).fetchone()

    if not profile:
        flash('Profile not found.', 'error')
        return redirect(url_for('catprofile.view_profiles'))  #Sends user back to the profile list page

    if profile['photo'] and profile['photo'] != "default.png":
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], profile['photo'])
        if os.path.exists(full_path):
            os.remove(full_path)  #Delete the file from storage

    with get_db_connection() as conn:
        conn.execute('UPDATE profiles SET photo = ? WHERE id = ?', ('',id,))
        conn.commit()

    flash('Profile picture removed successfully!', 'success')
    return redirect(url_for('catprofile.view_profiles'))  #Sends user back to the profile list page

@catprofile_bp.route('/profiles/<int:id>/delete', methods=['POST'])
def delete_profile(id):
    if not session.get('user'): #Ensure only logged in users can delete profile
        flash("You must be logged in to delete a profile.", "error")
        return redirect(url_for('auth.login')) #Sends user back to login page

    with get_db_connection() as conn:
        profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (id,)).fetchone()

    if not profile:
        flash('Profile not found.', 'error')
        return redirect(url_for('catprofile.view_profiles')) #Sends user back to the profile list page

    #Check if the current user is the creator of the profile
    if profile['creator'] != session['user']:
        flash("You are not authorized to delete this profile.", "error")
        return redirect(url_for('catprofile.view_profiles'))  #Sends user back to the profile list page

    full_path = os.path.join(app.config['UPLOAD_FOLDER'], profile['photo'])
    if os.path.exists(full_path):
        os.remove(full_path)

    with get_db_connection() as conn:
        conn.execute('DELETE FROM profiles WHERE id = ?', (id,))
        conn.commit()

    flash(f'Profile for "{profile["name"]}" has been deleted.', 'success')
    return redirect(url_for('catprofile.view_profiles')) #Sends user back to the profile list page

@catprofile_bp.route('/profiles/<int:id>/confirm_delete')
def confirm_delete(id):
    with get_db_connection() as conn:
        profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (id,)).fetchone()

    if not profile:
        flash('Profile not found.', 'error') 
        return redirect(url_for('catprofile.view_profiles')) #Sends user back to the profile list page

    #Check if the current user is the creator of the profile
    if session.get('user') is None or profile['creator'] != session['user']:
        flash('You are not authorized to delete this profile.', 'error')
        return redirect(url_for('catprofile.view_profiles')) #Sends user back to the profile list page

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

    app.run(debug=True)
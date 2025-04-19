import os
import sqlite3 #Connect to SQLite database to store and retrieve cat profile infromation
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename #Helps secure file uploads, preventing unsafe filenames that can cause errors or security issues

app = Flask(__name__) 
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png','jpg','jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    conn = sqlite3.connect('cat_profiles.db')  #Creates a connection to the database cat_profiles.db
    conn.row_factory = sqlite3.Row  #Access rows as dictionaries
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS #Verify if the file is in the allowed list

@app.before_request
def set_current_user():
    session['user'] = session.get('user', None) #Default to None if no user is logged in

@app.route('/profiles')
def view_profiles(): #View all cat profiles
    conn = get_db_connection() #Connect to the database to fetch cat profiles
    profiles = conn.execute('SELECT * FROM profiles').fetchall() #Get all cat profiles from the database
    conn.close() 
    return render_template('viewprofile.html', profiles=profiles, current_user=session.get('user'))

@app.route('/profiles/create', methods=['GET', 'POST'])
def create_profile():
    if not session.get('user'): #Ensure only logged in users can create profile
        flash("You must be logged in to create a profile.", "error")
        return redirect(url_for('view_profiles')) #Sends user back to profile list page

    #Handle removing the temporary profile picture during creation
    if request.method == 'POST' and 'remove_picture' in request.form:
        temp_picture = session.get('temp_profile_picture')
        if temp_picture:
            temp_picture_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_picture)
            if os.path.exists(temp_picture_path):
                os.remove(temp_picture_path)  #Delete the temporary picture from the filesystem
            session.pop('temp_profile_picture', None)  #Remove the reference from the session
        flash('Temporary profile picture removed.', 'success')
        return redirect(url_for('create_profile')) #Sends user back to create profile page

    #Create a new cat profile
    if request.method == 'POST':
        name = request.form['name'].strip().capitalize()
        gender = request.form['gender']
        color = request.form['color']
        description = request.form.get('description', '')  #Optional description
        photo = None

        #Check for duplicate names
        conn = get_db_connection()
        existing_names = conn.execute('SELECT name FROM profiles').fetchall()
        existing_names = [profile['name'].lower() for profile in existing_names]
        if name.lower() in existing_names:
            flash(f'The name "{name}" is already in use. Please choose a different one.', 'error')
            conn.close()
            return redirect(url_for('create_profile')) #Sends user back to the create profile page   

        #Validate that a profile picture is uploaded
        if 'profile_picture' not in request.files or request.files['profile_picture'].filename == '':
            flash('A profile picture is required!', 'error')
            return redirect(url_for('create_profile')) #Sendss user back to the create profile page

        #Handle file upload 
        file = request.files['profile_picture']
        if file.content_length is None or file.content_length > 2 * 1024 * 1024:
            flash("File size is too large. Please upload an image under 2MB.", "error") #Display error message to user if file size too big
            return redirect(url_for('create_profile')) #Sends user back to the create profile page

        if file and allowed_file(file.filename): #Checks if the file was uploaded in the correct format (png,jpg,jpeg)
            secure_file = secure_filename(file.filename)
            filename = f"{name.lower()}_{secure_file}" 
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath) 
            photo = filepath
        else:
            flash('Invalid file format. Please upload a PNG, JPG, or JPEG image.', 'error')
            return redirect(url_for('create_profile')) #Sends user back to the create profile page

        #Validate required fields
        if not photo or not name or not gender or not color:
            flash('Profile picture, name, gender and color are required!', 'error')
            return redirect(url_for('create_profile')) #Sends user back to the create profile page

        # Insert the new profile into the database
        conn = get_db_connection() #Connects to database
        conn.execute( 
            'INSERT INTO profiles (name, gender, color, description, photo, creator) VALUES (?, ?, ?, ?, ?, ?)',
            (name, gender, color, description, photo, session['user']) #Automatically assign the logged in user as the creator
        )
        conn.commit() #Save changes to the database
        conn.close()

        flash('Cat Profile created successfully!', 'success')
        return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    return render_template('createprofile.html')

@app.route('/profiles/<int:id>/edit', methods=['GET', 'POST'])
def edit_profile(id):
    if not session.get('user'): #Ensure only logged in users can create profile
        flash("You must be logged in to create a profile.", "error")
        return redirect(url_for('view_profiles')) #Sends user back to profile list page

    conn = get_db_connection() #Connect to the database to retrieve the profile information
    profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (id,)).fetchone() #Get the cat profile with the matching ID

    if not profile:
        flash('Cat Profile not found.', 'error') #Display error message to user if no profile is found
        return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    if request.method == 'POST':
        if 'remove_picture' in request.form:
            if profile['photo'] and os.path.exists(profile['photo']):
                os.remove(profile['photo'])  #Delete image from storage
                conn.execute('UPDATE profiles SET photo = NULL WHERE id = ?', (id,))  #Remove the photo link from the database
                conn.commit()
                flash('Profile picture removed successfully!', 'success')
            return redirect(url_for('edit_profile', id=id)) #Send user bck to edit profile page

        gender = request.form['gender']
        color = request.form['color']
        description = request.form.get('description', '')
        photo = profile['photo']

        #Handle file upload 
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.content_length is None or file.content_length > 2 * 1024 * 1024: 
                flash("File size is too large. Please upload an image under 2MB.", "error") #Display error message to user if file size too big
                return redirect(url_for('edit_profile', id=id)) #Sends user back to the edit profile page

            if file and allowed_file(file.filename):
                secure_file = secure_filename(file.filename)
                filename = f"{profile['name'].lower()}_{profile['id']}.{file.filename.rsplit('.', 1)[1].lower()}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                photo = filepath

        #Update profile in database
        conn.execute(
            'UPDATE profiles SET gender = ?, color = ?, description = ?, photo = ? WHERE id = ?',
            (gender, color, description, photo, id)
        )
        conn.commit()
        conn.close()

        flash('Profile updated successfully!', 'success') #Notify user profile updated successfully
        return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    return render_template('editprofiles.html', profile=profile)

@app.route('/profiles/remove_picture/<int:id>', methods=['POST'])
def remove_profile_picture(id):
    conn = get_db_connection()
    profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (id,)).fetchone()

    if not profile:
        flash('Profile not found.', 'error')
        return redirect(url_for('view_profiles'))  #Sends user back to the profile list page

    if profile['photo'] and os.path.exists(profile['photo']):
        os.remove(profile['photo'])  #Delete image from storage
        conn.execute('UPDATE profiles SET photo = NULL WHERE id = ?', (id,)) #Remove the photo link from the database for this profile
        conn.commit()

    conn.close()
    flash('Profile picture removed successfully!', 'success') #Notify user profile picture removed successfully
    return redirect(url_for('view_profiles'))  #Sends user back to the profile list page

@app.route('/profiles/<int:id>/delete', methods=['POST'])
def delete_profile(id):
    if not session.get('user'): #Ensure only logged in users can create profile
        flash("You must be logged in to create a profile.", "error")
        return redirect(url_for('view_profiles')) #Sends user back to profile list page

    conn = get_db_connection()
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

    conn.execute('DELETE FROM profiles WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash(f'Profile for "{profile["name"]}" has been deleted.', 'success')
    return redirect(url_for('view_profiles')) #Sends user back to the profile list page

@app.route('/profiles/<int:id>/confirm_delete')
def confirm_delete(id):
    conn = get_db_connection()
    profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (id,)).fetchone()

    if not profile:
        flash('Profile not found.', 'error') 
        return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    #Check if the current user is the creator of the profile
    if session.get('user') is None or profile['creator'] != session['user']:
        flash('You are not authorized to delete this profile.', 'error')
        return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    return render_template('confirmdelete.html', profile=profile)

if __name__ == '__main__':
    #Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    #Creates database table if it doesn't exist
    conn = get_db_connection()
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
    #id INTEGER PRIMARY KEY AUTOINFREMENT Adds a unique id for each entry
    #TEXT NOT NULL Adds a column for the name, gender ,color and profile picture which is a must to fill im
    #TEXT Adds a column for description which is not a must to fill in
    #creator TEXT NOT NULL Adds a column for creator which will be automatically filled in by the system 
    conn.close()

    app.run(debug=True)
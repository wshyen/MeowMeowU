import os
import sqlite3 #Connect to SQLite database to store and retrieve cat profile infromation
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename #Helps secure file uploads, preventing unsafe filenames that can cause errors or security issues
from flask_login import current_user

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
    if current_user.is_authenticated:  #Check if a user is logged in
        session['user'] = current_user.get_id()  #Store the logged-in user's ID in the session
    else:
        session['user'] = None  #No user is logged in

@app.route('/profiles')
def view_profiles(): #View all cat profiles
    conn = get_db_connection() #Connect to the database to fetch cat profiles
    profiles = conn.execute('SELECT * FROM profiles').fetchall() #Get all cat profiles from the database
    conn.close() 
    return render_template('viewprofile.html', profiles=profiles, current_user=session.get('user'))

@app.route('/profiles/create', methods=['GET', 'POST'])
def create_profile():
    #Create a new cat profile
    if request.method == 'POST':
        name = request.form['name'].strip().capitalize()
        existing_names = [profile['name'].lower() for profile in cat_profiles] #Creates a list of all profile names to check duplicates
        if name.lower() in existing_names:
            flash(f'The name "{name}" is already in use. Please choose a different one.', 'error') #Display error message to user that name is taken
            return redirect(url_for('create_profile')) #Sends user back to the create profile page
        gender = request.form['gender']
        color = request.form['color']
        description = request.form.get('description', '')  #Optional description
        photo = None

        #Validate name length
        if len(name) < 3 or len(name) > 15:
            flash('Name must be between 3 and 15 characters long.', 'error') #Display error message to user if name format not correct
            return redirect(url_for('create_profile')) #Sends user back to the create profile page

        #Handle file upload 
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']

            if file.content_length > 2 * 1024 * 1024:  
                flash("File size is too large. Please upload an image under 2MB.", "error") #Display error message to user if file size too big
                return redirect(url_for('create_profile'))

            if file and allowed_file(file.filename): #Checks if the file was uploaded in the correct format (png,jpg,jpeg)
                secure_file = secure_filename(file.filename)
                filename = f"{name.lower()}_{len(cat_profiles) + 1}.{file.filename.rsplit('.', 1)[1].lower()}" #len(cat_profiles) + 1 assigns an auto-incremented ID based on the number of existing profiles
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(photo_path) #Stores the uploaded file in a specific folder
                photo = f"static/uploads/{filename}"

        #Validate required fields
        if not name or not gender or not color:
            flash('Name, gender and color are required!', 'error')
            return redirect(url_for('create_profile')) #Sends user back to the create profile page

        # Insert the new profile into the database
        conn = get_db_connection() #Connects to database
        conn.execute( 
            'INSERT INTO profiles (name, gender, color, description, photo, creator) VALUES (?, ?, ?, ?, ?, ?)',
            (name, gender, color, description, photo, session['user']) #Use user session to track the profile creator
        )
        conn.commit() #Save changes to the database
        conn.close()

        flash('Cat Profile created successfully!', 'success')
        return redirect(url_for('view_profiles')) #Sends user back to the view profile page

    return render_template('createprofile.html')

@app.route('/profiles/<int:id>/edit', methods=['GET', 'POST'])
def edit_profile(id):
    #Edit existing cat profile
    profile = next((p for p in cat_profiles if p['id'] == id), None) #Finds the profile in the cat profiles list that matches the given ID and if no profile is found, it returns to None
    if not profile:
        flash('Cat Profile not found.', 'error') #Display error message to user if no profile is found
        return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    if request.method == 'POST':
        profile['gender'] = request.form['gender']
        profile['color'] = request.form['color']
        profile['description'] = request.form.get('description', '')

        #Handle file upload for profile picture
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']

            if file.content_length > 2 * 1024 * 1024:  
                flash("File size is too large. Please upload an image under 2MB.", "error") #Display error message to user if file size too big
                return redirect(url_for('create_profile')) #Sends user back to the create profile page

            if file and allowed_file(file.filename):
                secure_file = secure_filename(file.filename)
                filename = f"{profile['name'].lower()}_{profile['id']}.{file.filename.rsplit('.', 1)[1].lower()}"
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(photo_path)
                profile['photo'] = f"static/uploads/{filename}" #This stores image path inside the profile dictionary 

    flash('Profile updated successfully!', 'success') #Notify user profile updated successfully
    return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    return render_template('editprofiles.html', profile=profile)

@app.route('/profiles/remove_picture/<int:id>', methods=['POST'])
def remove_profile_picture(id):
    #Remove profile picture
    profile = next((p for p in cat_profiles if p['id'] == id), None)
    if not profile:
        flash('Profile not found.', 'error')
        return redirect(url_for('view_profiles'))  #Sends user back to the profile list page

    if profile['photo'] and os.path.exists(profile['photo']):
        os.remove(profile['photo'])  #Delete image from storage
        profile['photo'] = None  #Reset profile image

    flash('Profile picture removed successfully!', 'success') #Notify user profile picture removed successfully
    return redirect(url_for('view_profiles'))  #Sends user back to the profile list page

@app.route('/profiles/<int:id>/delete', methods=['POST'])
def delete_profile(id):
    #Delete a cat profile
    global cat_profiles
    profile = next((p for p in cat_profiles if p['id'] == id), None)
    if not profile:
        flash('Profile not found.', 'error')
        return redirect(url_for('view_profiles'))

    #Check if the current user is the creator of the profile
    if profile['creator'] != session['user']:
        flash('You are not authorized to delete this profile.', 'error')
        return redirect(url_for('view_profiles'))

    cat_profiles = [p for p in cat_profiles if p['id'] != id] #Remove profile from the list

    if profile['photo'] and os.path.exists(profile['photo']): #Delete the photo from the filesystem if it exists
        os.remove(profile['photo'])

    flash(f'Profile for "{profile["name"]}" has been deleted.', 'success')
    return redirect(url_for('view_profiles'))

@app.route('/profiles/<int:id>/confirm_delete')
def confirm_delete(id):
    #Confirm delete cat profile
    profile = next((p for p in cat_profiles if p['id'] == id), None)
    if not profile:
        flash('Profile not found.', 'error') 
        return redirect(url_for('view_profiles')) #Sends user back to the profile list page

    #Check if the current user is the creator of the profile
    if profile['creator'] != session['user']:
        flash('You are not authorized to delete this profile.', 'error')
        return redirect(url_for('view_profiles'))

    return render_template('confirmdelete.html', profile=profile)

if __name__ == '__main__':
    #Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)

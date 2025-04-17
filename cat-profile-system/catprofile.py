import os
from flask import Flask, render_template, flash

app = Flask(__name__) 
app.auth_key = 'auth_key'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png','jpg','jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#Temporary storage for cat profiles
cat_profiles = []

@app.route('/profiles')
def view_profiles(): #View all cat profiles
    return render_template('viewprofile.html', profiles=cat_profiles)

@app.route('/profiles/create', methods=['GET', 'POST'])
def create_profile():
    #Create new cat profile
    if request.method == 'POST':
        name = request.form['name'].strip().capitalize()
        gender = request.form['gender']
        color = request.form['color']
        description = request.form.get('description', '')  #Optional description
        photo = None

        #Validate name length
        if len(name) < 3 or len(name) > 15:
            flash('Name must be between 3 and 15 characters long.', 'error') #Display warning message to user 
            return redirect(url_for('create_profile'))

        #Handle file upload for profile pictures
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename): #Checks if the file was uploaded in the correct format (png,jpg,jpeg)
            filename = f"{name.lower()}_{len(cat_profiles) + 1}.{file.filename.rsplit('.', 1)[1].lower()}" #len(cat_profiles) + 1 assigns an auto-incremented ID based on the number of existing profiles
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(photo_path) #Stores the uploaded file in a specific folder
                photo = photo_path

        #Validate required fields
        if not name or not gender or not color:
            flash('Name, gender and color are required!', 'error')
            return redirect(url_for('create_profile'))

        #Create a new profile dictionary
        new_profile = {
            'id': len(cat_profiles) + 1,
            'name': name,
            'gender': gender,
            'color': color,
            'description': description,
            'photo': photo
        }
        cat_profiles.append(new_profile) #Add profile to the list

        flash('Cat Profile created successfully!', 'success') #Notify user profile created successfully return
        return redirect(url_for('view_profiles'))

    return render_template('createprofile.html')

if __name__ == '__main__':
    #Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)

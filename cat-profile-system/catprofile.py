import os
from flask import Flask, render_template

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
    return render_template('createprofile.html')

if __name__ == '__main__':
    #Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)

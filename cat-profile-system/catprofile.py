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

if __name__ == '__main__':
    #Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)

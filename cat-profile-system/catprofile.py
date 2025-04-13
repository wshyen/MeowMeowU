import os
from flask import Flask

app = Flask(__name__) 

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png','jpg','jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Temporary storage for cat profiles
cat_profiles = []

#Homepage route
@app.route('/')
def homepage():

from flask import Flask

app = Flask(__name__) #Initialize Flask

# Temporary storage for cat profiles
cat_profiles = []

#Homepage route
@app.route('/')
def homepage():

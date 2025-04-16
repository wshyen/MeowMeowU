from flask import Blueprint, render_template, request, flash, redirect, url_for
import re
from .models import User
from . import db
from werkzeug.security import generate_password_hash, check_password_hash

auth = Blueprint("auth", __name__)

@auth.route("/login", methods=["GET", "POST"])
def login():
    data = request.form
    print(data)
    return render_template("login.html")

@auth.route("/logout")
def logout():
    return "<p>Logout</p>"

@auth.route("/sign-up", methods=["GET", "POST"])
def sign_up():

    if request.method == "POST":

        email = request.form.get("email").lower()
        UserName = request.form.get("UserName")
        ps1 = request.form.get("ps1")
        ps2 = request.form.get("ps2")

        #check email address is mmu email onot
        if not re.match(r'^[\w\.-]+@student\.mmu\.edu\.my$', email): #"^" this means starting of the string and "$" this means closing
            flash("Only MMU student emails are allowed.", category="error")
        
        elif not re.match(r'^[A-Z][a-zA-Z0-9]{2,14}$', UserName):
            flash("Username must start with a capital letter and be 3 to 15 characters long.", category="error")

        elif len(ps1) < 7:
            flash('Password must be at least 7 characters.', category='error')

        #check ps
        elif ps1 != ps2:
            flash("Passwords do not match.", category="error")

        else: #if all correct
            new_user = User(email=email, UserName=UserName, ps=generate_password_hash(ps1, method="pbkdf2:sha256"))
            db.session.add(new_user) #add new user to database
            db.session.commit()
            flash("Account created successfully!", category="success")
            return redirect(url_for("auth.login"))
    
    return render_template("sign_up.html")
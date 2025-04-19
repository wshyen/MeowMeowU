from flask import Blueprint, render_template, request, flash, redirect, url_for #Flask is a web framework that allows developers to build web applications
import re
from .models import User
from . import db
from werkzeug.security import generate_password_hash, check_password_hash #for password hashing and verification
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint("auth", __name__) #a Blueprint for authentication routes, Blueprint is like a container for related routes and functions

@auth.route("/login", methods=["GET", "POST"]) #POST is a HTTP request methods that send data to the server
#HTTP request methods are ways for a web browser or app to communicate with a server over the internet
def login():
    if request.method == "POST":
        email = request.form.get("email")
        ps = request.form.get("ps")

        user = User.query.filter_by(email=email).first()
        if user: #check user exists onot
            if check_password_hash(user.ps, ps):
                flash("Logged in successfully!", category="success") #pop a message out
                login_user(user, remember=True)
                return redirect(url_for("views.home"))
            else:
                flash("Incorrect password, please try again.", category="error")
        else:
            flash("Email does not exist!", category="error")

    return render_template("login.html", user=current_user)

@auth.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    if request.method == "POST":
        logout_user()
        flash("You have been logged out successfully.", category="success")
        return redirect(url_for("views.home"))
    
    return render_template("logout.html", user=current_user)

@auth.route("/sign-up", methods=["GET", "POST"])
def sign_up():

    if request.method == "POST":

        email = request.form.get("email").lower()
        UserName = request.form.get("UserName")
        ps1 = request.form.get("ps1")
        ps2 = request.form.get("ps2")

        user = User.query.filter_by(email=email).first()
        
        if user:
            flash("Email already exist!", category="error")

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
            login_user(user, remember=True)
            flash("Account created successfully!", category="success")
            return redirect(url_for("auth.login"))
    
    return render_template("sign_up.html", user=current_user)
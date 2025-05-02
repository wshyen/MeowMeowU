from flask import Blueprint, render_template, request, flash, redirect, url_for, session #Flask is a web framework that allows developers to build web applications
import re
from .models import User
from . import db
from werkzeug.security import generate_password_hash, check_password_hash #for password hashing and verification
from werkzeug.utils import secure_filename #handling file uploads
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy.exc import IntegrityError
import os

auth = Blueprint("auth", __name__) #a Blueprint for authentication routes, Blueprint is like a container for related routes and functions

#configuration for file uploads
UPLOAD_FOLDER = 'static/Userprofile'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    #Check if the uploaded file has an allowed extension
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@auth.route("/login", methods=["GET", "POST"]) #POST is a HTTP request methods that send data to the server
#HTTP request methods are ways for a web browser or app to communicate with a server over the internet
def login():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
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
            flash("Invalid email or password.", category="error")

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
        email = request.form.get("email").strip().lower()
        UserName = request.form.get("UserName")
        ps1 = request.form.get("ps1")
        ps2 = request.form.get("ps2")
        secret_answer = request.form.get("secret_answer").strip().lower()
        hashed_secret_answer = generate_password_hash(secret_answer, method="pbkdf2:sha256")

        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            flash("Email already exist!", category="error")
            return render_template("sign_up.html", user=current_user)

        elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            flash("Invalid email address.", category="error")

        elif not re.match(r'^[A-Z][a-zA-Z0-9]{2,14}$', UserName):
            flash("Username must start with a capital letter and be 3 to 15 characters long.", category="error")

        elif len(ps1) < 7:
            flash('Password must be at least 7 characters.', category='error')

        #check ps
        elif ps1 != ps2:
            flash("Passwords do not match.", category="error")

        elif not secret_answer:
            flash("Secret question answer is required.", category="error")

        else: #if all correct
            new_user = User(email=email,UserName=UserName,ps=generate_password_hash(ps1, method="pbkdf2:sha256"),
                            secret_answer=hashed_secret_answer)
            db.session.add(new_user) #add new user to database

            try:
                db.session.commit()
                login_user(new_user, remember=True)
                flash("Account created successfully!", category="success")
                return redirect(url_for("auth.login"))
            except IntegrityError:
                db.session.rollback()
                flash("An error occurred while creating the account. Please try again.", category="error")
            
    return render_template("sign_up.html", user=current_user)

@auth.route("/user-profile", methods=["GET", "POST"])
@login_required
def user_profile():
    return render_template("user_profile.html", user=current_user)

@auth.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_ps = request.form.get("current_password")
        new_ps = request.form.get("new_password")
        confirm_ps = request.form.get("confirm_password")

        if not current_ps or not new_ps or not confirm_ps:
            flash("All fields are required.", category="error")
        elif not check_password_hash(current_user.ps, current_ps):
            flash("Current password is incorrect.", category="error")
        elif len(new_ps) < 7:
            flash("New password must be at least 7 characters long.", category="error")
        elif new_ps != confirm_ps:
            flash("New passwords do not match.", category="error")
        else:
            #update the password
            current_user.ps = generate_password_hash(new_ps, method="pbkdf2:sha256")
            db.session.commit()
            flash("Password changed successfully!", category="success")
            return redirect(url_for("auth.user_profile"))

    return render_template("change_password.html", user=current_user)

@auth.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        secret_answer = request.form.get("secret_answer").strip().lower()
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Invalid email.", category="error")
        elif not check_password_hash(user.secret_answer, secret_answer):
            flash("Invalid answer.", category="error")
        elif len(new_password) < 7:
            flash("New password must be at least 7 characters.", category="error")
        elif new_password != confirm_password:
            flash("Passwords do not match.", category="error")
        else:
            user.ps = generate_password_hash(new_password, method="pbkdf2:sha256")
            db.session.commit()
            flash("Password has been reset successfully!", category="success")
            return redirect(url_for("auth.login"))

    return render_template("reset_password.html", user=current_user)

@auth.route("/view_profiles", methods=["GET", "POST"])
def view_profiles():
    return render_template("viewprofile.html", user=current_user)

@auth.route("/create_profiles", methods=["GET", "POST"])
def create_profiles():
    return render_template("createprofile.html", user=current_user)

@auth.route("/update-profile", methods=["GET", "POST"])
@login_required
def update_profile():
    if request.method == "POST":
        changes_made = False #track changes

        username = request.form.get("username")
        if username and username != current_user.UserName:
            if len(username) < 3 or len(username) > 15 or not username[0].isupper():
                flash("Username must be 3-15 characters long and start with a capital letter.", category="error")
                return redirect(url_for("auth.update_profile"))
            else:
                current_user.UserName = username
                changes_made = True

        bio = request.form.get("bio")
        if bio and bio != current_user.bio:
            if len(bio) > 200:
                flash("Bio must not exceed 200 characters.", category="error")
            else:
                current_user.bio = bio
                changes_made = True

        status = request.form.get("status")
        if status and status.strip() != current_user.status:
            current_user.status = status.strip()
            changes_made = True

        birthday = request.form.get("birthday")
        if birthday and birthday != current_user.birthday:
            current_user.birthday = birthday
            changes_made = True
            
        hobby = request.form.get("hobby")
        if hobby and hobby != current_user.hobby:
            current_user.hobby = hobby
            changes_made = True

        mbti = request.form.get("mbti")
        valid_mbti = {"INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
                      "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"}
        if mbti and mbti.upper() != current_user.mbti.upper():
            if mbti.upper() not in valid_mbti:
                flash("Invalid MBTI type selected.", category="error")
                return redirect(url_for("auth.update_profile"))
            else:
                current_user.mbti = mbti.upper()
                changes_made = True

        #handle file uploads
        for file_type in ["profile_picture", "cover_photo"]:
            if file_type in request.files:
                file = request.files[file_type]
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(UPLOAD_FOLDER, filename))
                    setattr(current_user, file_type, filename)
                    changes_made = True
                else:
                    flash(f"Invalid file format for {file_type}. Only PNG, JPG, JPEG allowed.", category="error")
                    return redirect(url_for("auth.update_profile"))

        if not changes_made:
            flash("No changes were made to your profile.", category="info")
            return redirect(url_for("auth.update_profile"))

        try:
            db.session.commit()
            flash("Profile updated successfully!", category="success")
        except IntegrityError:
            flash("An error occurred while updating the profile. Please try again.", category="error")
            return redirect(url_for("auth.update_profile"))

        return redirect(url_for("auth.user_profile"))

    return render_template("update_profile.html", user=current_user)



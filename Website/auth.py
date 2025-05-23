from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory #Flask is a web framework that allows developers to build web applications
import re
from .models import User, Story, Report
from . import db
from werkzeug.security import generate_password_hash, check_password_hash #for password hashing and verification
from werkzeug.utils import secure_filename #handling file uploads
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy.exc import IntegrityError
import os
from datetime import datetime, timedelta

auth = Blueprint("auth", __name__) #a Blueprint for authentication routes, Blueprint is like a container for related routes and functions

#configuration for file uploads
UPLOAD_FOLDER = 'Website/static/Userprofile'
UPLOADFOLDER = 'Website/static/story'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

DEFAULT_PROFILE_PICTURE = "default_profilepic.png"
DEFAULT_COVER_PHOTO = "default_cover.png"

#makesure the upload folder exists before saving files
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
        email = request.form.get("email", "").strip().lower()
        Name = request.form.get("Name")
        ps1 = request.form.get("ps1", "").strip()
        ps2 = request.form.get("ps2", "").strip()
        secret_answer = request.form.get("secret_answer", "").strip().lower()

        #check if the email is empty
        if not email:
            flash("Please enter an email address.", category="error")
            return render_template("sign_up.html", user=current_user)

        #existing email check
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already exists!", category="error")
            return render_template("sign_up.html", user=current_user)

        #validate email format
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            flash("Invalid email address format.", category="error")
            return render_template("sign_up.html", user=current_user)

        #validate Name format (At least 3 characters, first letter uppercase)
        if not Name or len(Name) < 3 or not Name[0].isupper():
            flash("Name must be at least 3 characters long and start with a capital letter.", category="error")
            return render_template("sign_up.html", user=current_user)

        #ensure secret_answer exists before hashing
        if not secret_answer:
            flash("Secret question answer is required.", category="error")
            return render_template("sign_up.html", user=current_user)

        hashed_secret_answer = generate_password_hash(secret_answer, method="pbkdf2:sha256")

        #password validation
        if len(ps1) < 7:
            flash("Password must be at least 7 characters long.", category="error")
            return render_template("sign_up.html", user=current_user)

        if ps1 != ps2:
            flash("Passwords do not match.", category="error")
            return render_template("sign_up.html", user=current_user)

        #create new user in the database
        new_user = User(email=email, Name=Name, ps=generate_password_hash(ps1, method="pbkdf2:sha256"),
                        secret_answer=hashed_secret_answer)

        db.session.add(new_user)

        try:
            db.session.commit()
            login_user(new_user, remember=True)
            flash("Account created successfully!", category="success")
            return redirect(url_for("auth.login"))
        except IntegrityError:
            db.session.rollback()
            flash("An error occurred while creating the account. Please try again.", category="error")
            return render_template("sign_up.html", user=current_user)

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

@auth.route("/update-profile", methods=["GET", "POST"])
@login_required
def update_profile():
    if request.method == "POST":
        changes_made = False #track changes

        name = request.form.get("name")
        if name and name != current_user.Name:
            if len(name) < 3 or len(name) > 15 or not name[0].isupper():
                flash("Name must be 3-15 characters long and start with a capital letter.", category="error")
                return redirect(url_for("auth.update_profile"))
            else:
                current_user.Name = name
                changes_made = True

        bio = request.form.get("bio")
        if bio != current_user.bio:
            if bio and len(bio) > 200:
                flash("Bio must not exceed 200 characters.", category="error")
                return redirect(url_for("auth.update_profile"))
            current_user.bio = bio.strip() if bio else None
            changes_made = True

        status = request.form.get("status")
        if status != current_user.status:
            current_user.status = status.strip() if status else None
            changes_made = True

        birthday = request.form.get("birthday")
        if birthday:
            try:
                valid_birthday = datetime.strptime(birthday, "%Y-%m-%d").date()
                if valid_birthday != current_user.birthday:
                    current_user.birthday = valid_birthday
                    changes_made = True
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", category="error")
                return redirect(url_for("auth.update_profile"))
        elif current_user.birthday is not None:
            current_user.birthday = None
            changes_made = True

        hobby = request.form.get("hobby")
        if hobby != current_user.hobby:
            current_user.hobby = hobby if hobby else None
            changes_made = True

        mbti = request.form.get("mbti")
        if mbti != current_user.mbti:
            current_user.mbti = mbti if mbti else None
            changes_made = True

        #handle file uploads
        for file_type, default_image in [("profile_picture", DEFAULT_PROFILE_PICTURE), ("cover_photo", DEFAULT_COVER_PHOTO)]:
            if request.form.get(f"clear_{file_type}"):  # Reset to default if checkbox checked
                setattr(current_user, file_type, default_image)
                changes_made = True
            elif file_type in request.files and request.files[file_type].filename != "":
                file = request.files[file_type]
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)  # Ensure file is saved
                    setattr(current_user, file_type, filename)  # Store filename in DB
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

#cat story
@auth.route("/cat_story", methods=["GET"])
def cat_story():
    PER_PAGE = 6
    page = request.args.get("page", 1, type=int)
    selected_month = None
    selected_year = None

    #get unique month and year values for the dropdown
    unique_dates = Story.query.with_entities(
        db.func.extract("month", Story.created_at).label("month"),
        db.func.extract("year", Story.created_at).label("year")
    ).distinct().order_by(Story.created_at.desc()).all()

    #filtering logic based on selected month and year
    month_param = request.args.get("month")
    if month_param:
        try:
            month, year = map(int, month_param.split("-"))
            selected_month = month
            selected_year = year
            query = Story.query.filter(
                db.func.extract("month", Story.created_at) == month,
                db.func.extract("year", Story.created_at) == year
            )
        except ValueError:
            query = Story.query
    else:
        query = Story.query

    #order by newest first
    query = query.order_by(Story.created_at.desc())

    #paginate the query result
    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)
    latest_stories = pagination.items
    has_next = pagination.has_next
    has_prev = pagination.has_prev

    return render_template(
        "cat_story.html",
        user=current_user,
        latest_stories=latest_stories,
        unique_dates=unique_dates,
        selected_month=selected_month,
        selected_year=selected_year,
        page=page,
        has_next=has_next,
        has_prev=has_prev
    )

@auth.route('/view_story/<int:story_id>')
def view_story(story_id):
    story = Story.query.get_or_404(story_id)
    return render_template("view_story.html", story=story, user=current_user)

@auth.route('/my_story')
def my_story():

    if not current_user.is_authenticated:
        flash("You must be logged in to view your story!", category="error")
        return redirect(url_for('auth.login'))

    #retrieve user stories sorted by latest first
    user_stories = Story.query.filter_by(user_id=current_user.id).order_by(Story.created_at.desc()).all()

    total = len(user_stories)
    index = request.args.get('index', 0, type=int)

    #ensure index remains within valid bounds
    index = max(0, min(index, total - 1))

    return render_template(
        "my_story.html",
        user_stories=user_stories,
        index=index,
        total=total,
        user=current_user
    )

@auth.route('/share_story', methods=['GET', 'POST'])
def share_story():
    if not current_user.is_authenticated:
        flash("You must be logged in to share your story!", category="error")
        return redirect(url_for('auth.login'))

    #get the latest story by the current user
    latest_story = Story.query.filter_by(user_id=current_user.id).order_by(Story.created_at.desc()).first()

    if latest_story:
        #calculate the next allowed date for sharing
        next_allowed_date = latest_story.created_at + timedelta(days=30)
        if datetime.utcnow() < next_allowed_date:
            flash(f"You can only share one story per month. Your next allowed story date is {next_allowed_date.strftime('%Y-%m-%d')}.", category="error")
            return redirect(url_for('auth.cat_story'))

    if request.method == "POST":
        image = request.files.get("image")
        caption = request.form.get("caption", "").strip()
        story = request.form.get("story", "").strip()

        #validate the image
        if not image or not allowed_file(image.filename):
            flash("Invalid or missing image. Only PNG, JPG, JPEG files are allowed.", category="error")
            return redirect(url_for("auth.share_story"))

        #validate the story length
        if len(story.split()) < 200:
            flash("Your story must have more than 200 words.", category="error")
            return redirect(url_for("auth.share_story"))

        #save the image
        filename = secure_filename(image.filename)
        image_path = os.path.join(UPLOADFOLDER, filename)
        image.save(image_path)

        new_story = Story(
            image_filename=filename,
            caption=caption,
            story_text=story,
            user_id=current_user.id,
            created_at=datetime.utcnow()
        )

        db.session.add(new_story)
        try:
            db.session.commit()
            flash("Your story has been shared successfully!", category="success")
            return redirect(url_for("auth.my_story"))
        except IntegrityError:
            db.session.rollback()
            flash("An error occurred while saving your story. Please try again.", category="error")

    return render_template("share_story.html", user=current_user)

#route to serve uploaded images from the static/story folder
@auth.route('/static/story/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('static/story', filename)

#content moderation
@auth.route('/report/<int:post_id>', methods=['GET', 'POST'])
def report_page(post_id):

    if not current_user.is_authenticated:
        flash("You must be logged in to report!", category="error")
        return redirect(url_for('auth.login'))

    return render_template('report_page.html', post_id=post_id, user=current_user)

@auth.route("/submit_report", methods=["POST"])
@login_required
def submit_report():
    report_type = request.form.get("report_type")
    post_id = request.form.get("post_id")
    story_id = request.form.get("story_id")
    comment_id = request.form.get("comment_id")
    reason = request.form.get("reason")
    other_reason = request.form.get("otherReason").strip()
    details = request.form.get("details")

    #ensure "Other" has a custom reason
    if reason == "other" and not other_reason:
        flash("You selected 'Other' but didn't provide a reason. Please enter a valid reason.", category="error")
        return redirect(url_for("auth.report_page", post_id=post_id))  

    report_reason = other_reason if reason == "other" else reason

    #create a new Report entry
    new_report = Report(
        user_id=current_user.id,
        post_id=post_id if report_type == "post" else None,
        story_id=story_id if report_type == "story" else None,
        comment_id=comment_id if report_type == "comment" else None,
        reason=report_reason,
        details=details,
    )

    db.session.add(new_report)
    db.session.commit()
    flash("Report submitted successfully! Thank you for your feedback.", category="success")

    return redirect(url_for("auth.report_page",post_id=post_id))
import sqlite3
import os
from flask import Flask, render_template, request

app = Flask(__name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'cat-profile-system', 'cat_profiles.db')
    db_path = os.path.abspath(db_path)
    conn = sqlite3.connect(db_path)
    return conn

@app.route('/')
def search():
    return render_template("search-feature.html")

@app.route('/cat-list')
def cat_list():
    name = request.args.get("name", "").lower()
    gender = request.args.get("gender", "")
    color = request.args.get("color", "")

    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM profiles WHERE 1=1"
    cat_filters = [] 

    if name:
        query += " AND LOWER(name) LIKE ?"
        cat_filters.append(f"%{name}%")  #to find names containing the input 'name' anywhere in the text
    if gender:
        query += " AND gender = ?"
        cat_filters.append(gender)
    if color:
        query += " AND color = ?"
        cat_filters.append(color)
    
    cursor.execute(query, cat_filters)
    profiles = cursor.fetchall()
    conn.close()

    if profiles:
        return render_template("cat-list.html", profiles=profiles)
    else:
        return render_template("cat-list.html", message="No cats found matching your criteria.")


 
@app.route('/viewprofile')
def view_profile():
    name = request.args.get("name", "").lower()
    selected_cat = None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE LOWER(name) = ?", (name.lower(),))
    selected_cat = cursor.fetchone()
    conn.close()

    if selected_cat:
        return render_template("viewprofile.html", cat=selected_cat)
    
if __name__ == '__main__':
    app.run(debug=True)
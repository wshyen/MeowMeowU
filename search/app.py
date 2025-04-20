import sqlite3
from flask import Flask, render_template, request

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('cat_profiles.db') 
    conn.row_factory = sqlite3.Row
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
    query = "SELECT * FROM cats WHERE 1=1"

    if name:
        query += " AND name LIKE ?"
    if gender:
        query += " AND gender = ?"
    if color:
        query += " AND color LIKE ?"
    
    cursor.execute(query, 
                   (f"%{name}%", gender, f"%{color}%"))
    cats = cursor.fetchall()
    conn.close()

    if cats:
        return render_template("cat-list.html", cats=cats)
    else:
        return render_template("cat-list.html", message="No cats found matching your criteria.")


 
@app.route('/viewprofile')
def view_profile():
    name = request.args.get("name", "").lower()
    selected_cat = None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cats WHERE name = ?", (name,))
    selected_cat = cursor.fetchone()
    conn.close()

    if selected_cat:
        return render_template("viewprofile.html", cat=selected_cat)
    
if __name__ == '__main__':
    app.run(debug=True)
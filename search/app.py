import sqlite3
import os
from flask import Flask, render_template, request

app = Flask(__name__, static_folder='../cat-profile-system/static', static_url_path='/static')

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'cat-profile-system', 'cat_profiles.db')
    db_path = os.path.abspath(db_path) 
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def search():
    return render_template("search_feature.html")

@app.route('/cat_list')
def cat_list():
    name = request.args.get("name", "").lower()
    gender = request.args.get("gender", "")
    color = request.args.get("color", "")
    sort = request.args.get("sort") 

    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM profiles WHERE 1=1"
    cat_filters = [] 
    
    if name:
        query += " AND LOWER(name) LIKE ?"
        cat_filters.append(f"%{name}%")  #to find names containing the input 'name' anywhere in the text

    if gender and gender != "Not sure":
        query += " AND gender = ?"
        cat_filters.append(gender)

    if color:
        query += " AND color = ?"
        cat_filters.append(color)

    if sort == "name_asc":
        query += " ORDER BY name ASC"
    elif sort == "name_desc":
        query += " ORDER BY name DESC"

    cursor.execute(query, cat_filters)
    profiles = cursor.fetchall()
    conn.close()

    if profiles:
        return render_template("cat_list.html", profiles=profiles)
    else:
        return render_template("cat_list.html", message="No cats found matching your criteria.")
 
@app.route('/single_profile')
def single_profile():
    name = request.args.get("name", "").lower()
    selected_cat = None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE LOWER(name) = ?", (name.lower(),))
    selected_cat = cursor.fetchone()
    conn.close()

    if selected_cat:
        return render_template("single_profile.html", cat=selected_cat)
    
    
    
if __name__ == '__main__':
    # 调试：列出所有表名
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print("📋 数据库中存在的表：", cursor.fetchall())
    conn.close()

    app.run(debug=True)
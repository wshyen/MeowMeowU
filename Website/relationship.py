import os
import sqlite3
from flask import Blueprint, g, render_template
from flask import request, redirect, url_for
from flask_login import current_user
from graphviz import Digraph


relationship_bp = Blueprint('relationship', __name__, template_folder='templates')

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'datebase.db')
    db_path = os.path.abspath(db_path) 
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def generate_graph(relations):
    dot = Digraph(comment='Cat Relationship Tree')

    for rel in relations:
        dot.node(rel['catA_name'], rel['catA_name'])
        dot.node(rel['catB_name'], rel['catB_name'])
        dot.edge(rel['catA_name'], rel['catB_name'], label=rel['relation_type'])

    return dot.pipe(format='svg').decode('utf-8')

@relationship_bp.route('/relationship_feature', methods=['GET', 'POST'])
def relationship_feature():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            catA_id = request.form.get('catA_id')
            catB_id = request.form.get('catB_id')
            relation_type = request.form.get('relation_type')
            other_relation = request.form.get('other_relation')

            if relation_type == 'Other' and other_relation and other_relation.strip():
                relation_type = other_relation.strip()

            if catA_id and catB_id and relation_type and catA_id != catB_id:
                cursor.execute(
                    "INSERT INTO cat_relationship (catA_id, catB_id, relation_type) VALUES (?, ?, ?)",
                    (catA_id, catB_id, relation_type)
                )
                conn.commit()
            return redirect(url_for('relationship.relationship_feature'))

        elif action == 'delete':
            rel_id = request.form.get('rel_id')
            if rel_id:
                cursor.execute("DELETE FROM cat_relationship WHERE id = ?", (rel_id,))
                conn.commit()
            return redirect(url_for('relationship.relationship_feature'))


    cats = cursor.execute("SELECT id, name, gender, photo FROM profiles").fetchall()
    relations = cursor.execute("""
        SELECT cr.id, cr.catA_id, cr.catB_id, cr.relation_type,
            p1.name AS catA_name, p1.photo AS catA_photo,
            p2.name AS catB_name, p2.photo AS catB_photo
        FROM cat_relationship cr
        JOIN profiles p1 ON cr.catA_id = p1.id
        JOIN profiles p2 ON cr.catB_id = p2.id
    """).fetchall()

    graph_svg = generate_graph(relations)

    conn.close()
    return render_template('relationship.html', user=current_user, profiles=cats, relations=relations, tree_img=graph_svg 
    )


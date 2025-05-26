import os
import sqlite3
from flask import Blueprint, g, render_template, request, redirect, url_for, current_app
from flask_login import current_user
from graphviz import Digraph


relationship_bp = Blueprint('relationship', __name__, template_folder='templates')

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'datebase.db')
    db_path = os.path.abspath(db_path) 
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def generate_graph(relations, filename='cat_relationship_tree'):
    from graphviz import Digraph
    import os
    from flask import current_app, url_for

    dot = Digraph(comment='Cat Relationship Tree', format='svg')
    dot.attr('node', shape= "none", margin='0.2,0.2')
    dot.attr(pad="0.5", margin="0.5", dpi="80") 
    dot.attr('edge', arrowsize='0.6', penwidth='1.2')

    added_nodes = set()
    for rel in relations:
        for cat_id, cat_name, cat_photo in [
            (rel['catA_id'], rel['catA_name'], rel['catA_photo']),
            (rel['catB_id'], rel['catB_name'], rel['catB_photo'])
        ]:
            if cat_name not in added_nodes:
                label = f'''<
                [PIC]<BR/>{cat_name}
                >'''
                dot.node(cat_name, label=label)
                added_nodes.add(cat_name)
                # ...existing code...

        dot.edge(rel['catA_name'], rel['catB_name'], label=rel['relation_type'])

    output_dir = os.path.join(current_app.static_folder, 'graphs')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    dot.render(output_path, format='svg', cleanup=True)

    return url_for('static', filename=f'graphs/{filename}.svg')
# ...existing code...

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

    graph_png = generate_graph(relations)

    cat_photos = {cat['name']: url_for('static', filename=f'uploads/{cat["photo"]}') for cat in cats}
    return render_template(
        'relationship.html',
        user=current_user,
        profiles=cats,
        relations=relations,
        tree_img=graph_png,
        cat_photos=cat_photos

    )    

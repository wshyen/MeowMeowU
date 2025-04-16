from flask import Flask, render_template, request

app = Flask(__name__)

cat_data = [
    {"name": "Bubble", "gender": "Female", "color": "Calico", "image": "bubble.jpg"},
    {"name": "Tom", "gender": "Male", "color": "Gray(Blue)", "image": "tom.jpg"},
]

@app.route('/')
def search():
    return render_template("search-feature.html")

@app.route('/cat-list')
def cat_list():
    name = request.args.get("name", "").lower()
    gender = request.args.get("gender", "")
    color = request.args.get("color", "")

    filtered_cats = []
    for cat in cat_data:
        if (not name or name in cat["name"].lower()) and \
           (not gender or gender == cat["gender"]) and \
           (not color or color == cat["color"]):
            filtered_cats.append(cat)

    print(filtered_cats)

    return render_template("cat-list.html", cats=filtered_cats)

if __name__ == '__main__':
    app.run(debug=True)
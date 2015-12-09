from flask import Flask, abort, jsonify, request, render_template, redirect, url_for
import wikibard, wikiserver
from  werkzeug.debug import get_current_traceback
import yaml
import dotmatrix
from flask.ext.cors import CORS
import wikipedia

print_to_dot_matrix = True

# EB looks for an 'application' callable by default.
application = Flask(__name__)
cors = CORS(application, resources={r"/api/*": {"origins": "*"}})

@application.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@application.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    query = query.replace("_", " ")
    print("Searching!")
    print(query)
    results = wikipedia.search(query)
    print(results)
    updated_results = []
    for result in results:
        updated_results.append(result.replace(" ", "_"))
    return jsonify(list=updated_results)


@application.route('/compose', methods=['POST'])
def compose():
    title = request.form.get("query")
    try:
        page = wikipedia.page(title.replace("_", " "))
    except wikipedia.exceptions.DisambiguationError:
        return redirect(url_for('index'))

    if not page:
        return redirect(url_for('index'))
    print("Composing poem for " + title)
    poem = wikiserver.poemForPageTitle(title)
    poem_lines = poem.split('\n')
    title = title.replace("_", " ")
    images = wikiserver.imagesForPageTitle(title)

    if print_to_dot_matrix:
        dotmatrix.printPoem(title, poem_lines)

    if images:
        image = images[0]
        return render_template('poem.html', title=title, poem_lines=poem_lines, image=image)
    else:
        return render_template('poem.html', title=title, poem_lines=poem_lines)

# run the app.
if __name__ == "__main__":
    application.debug = False
    application.testing = True
    application.run(threaded=True)

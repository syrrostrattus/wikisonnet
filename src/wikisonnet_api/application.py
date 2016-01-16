# Copyright 2015. Amazon Web Services, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import json

import flask
from flask import request, Response, jsonify, session
import wikiconnector
from multiprocessing import Manager, Queue, cpu_count, Process
from flask.ext.cors import CORS
# from IPython import embed

import dotmatrix

print_to_dotmatrix = False

# Default config vals
THEME = 'default' if os.environ.get('THEME') is None else os.environ.get('THEME')
FLASK_DEBUG = 'false' if os.environ.get('FLASK_DEBUG') is None else os.environ.get('FLASK_DEBUG')

# Create the Flask app
application = flask.Flask(__name__)
cors = CORS(application, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://159.203.110.230:3000", "http://wikison.net"], "supports_credentials": True}})

# Load config values specified above
application.config.from_object(__name__)

application.secret_key = 'this is a test secret key'

# Load configuration vals from a file
application.config.from_pyfile('application.config', silent=True)
HOST_IP = 'localhost'if application.config.get('HOST_IP') is None else application.config.get('HOST_IP')
DB_CONFIG = 'local'if application.config.get('DB_CONFIG') is None else application.config.get('DB_CONFIG')
PROCESS_COUNT = 1 if application.config.get('PROCESS_COUNT') is None else application.config.get('PROCESS_COUNT')
dbconfig = wikiconnector.dbconfigForName(DB_CONFIG)

# Only enable Flask debugging if an env var is set to true
application.debug = application.config['FLASK_DEBUG'] in ['true', 'True']

# Pool of worker processes
process_count = 4
try:
    process_count = cpu_count();
except:
    print "Could not determine cpu_count--defaulting to {} processes".format(process_count)
task_queue = None

def worker(task_queue):
    for func, args, callback, userinfo in iter(task_queue.get, 'STOP'):
        res = apply(func, args)
        if callback:
            callback(res, userinfo)

@application.route('/')
def welcome():
    theme = application.config['THEME']
    page_name = wikiconnector.getRandomPoemTitle(dbconfig)
    return flask.render_template('index.html', theme=theme, page_name=page_name)

# @application.route('/api/v2/pages/<page_id>/poems', methods=['GET', 'POST'])
# def compose(page_id):
#     if not session.get('id'):
#         session_id = wikiconnector.createSession(dbconfig)
#         session['id'] = session_id
#     poem_dict = wikiconnector.getCachedPoemForPage(dbconfig, page_id)
#     if poem_dict is None:
#         poem_dict = wikiconnector.getCachedPoemForPage(dbconfig, page_id, complete=False)
#     if poem_dict is None:
#         poem_dict = wikiconnector.writeNewPoemForPage(dbconfig, page_id)
#     return jsonify(poem_dict)

@application.route('/api/v2/poems', methods=['POST'])
def compose():
    if not session.get('id'):
        session_id = wikiconnector.createSession(dbconfig)
        session['id'] = session_id
    title = request.form.get("poemTitle")
    page_id = wikiconnector.getPageId(dbconfig, title)
    poem_dict = wikiconnector.getCachedPoemForPage(dbconfig, page_id, True, session['id'])
    if poem_dict is not None:
        if 'id' in session:
            wikiconnector.addPoemToSession(dbconfig, poem_dict['id'], session['id'])
        print_poem(page_id, poem_dict)
    if poem_dict is None:
        poem_dict = wikiconnector.getCachedPoemForPage(dbconfig, page_id, False)
    if poem_dict is None:
        poem_dict = wikiconnector.writeNewPoemForPage(dbconfig, page_id, task_queue)
    return jsonify(poem_dict)

@application.route('/api/v2/poems/<poem_id>', methods=['GET'])
def lookup(poem_id):
    poem_dict = wikiconnector.getSpecificPoem(dbconfig, poem_id)
    if poem_dict['complete']:
        if 'id' in session:
            wikiconnector.addPoemToSession(dbconfig, poem_dict['id'], session['id'])
        print_poem(poem_dict['starting_page'], poem_dict)
    return jsonify(poem_dict)

def print_poem(page_id, poem_dict):
    if print_to_dotmatrix:
        title = wikiconnector.getPageTitle(dbconfig, page_id)
        lines = [r["text"] for r in poem_dict["lines"]]
        dotmatrix.printPoem(title, lines)

def run():
    global task_queue
    task_queue = Manager().Queue()
    for i in range(process_count):
        Process(target=worker, args=(task_queue,)).start()
    application.run(host='0.0.0.0', port=8000)

if __name__ == '__main__':
    run()
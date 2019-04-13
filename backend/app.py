from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
import time
import os

from query_module.QueryModule import QueryModule
from response_module.ResponseModule import ResponseModule
from management_module.ManagementModule import ManagementModule
from conf.Error import UploadFileError, AuthenticationError
from conf.Success import UploadFileSuccess
from conf.Logger import Logger
from authenitcation.security import generate_token, verify_token
from authenitcation.db import Authenticator

"""
    Initialize modules
"""
query_module = QueryModule()
response_module = ResponseModule()
management_module = ManagementModule()
authenticator = Authenticator()

"""
    Logger configurations. By default all are set to DEBUG level.
    Change the level in setLevel to suit whatever your needs are.
    Available levels from highest severity to lowest are:
        CRITICAL
        ERROR
        WARNING
        INFO
        DEBUG
"""
logger = Logger(__name__).log
logger.setLevel(logging.INFO)
query_module_logger = logging.getLogger('query_module.QueryModule')
query_module_logger.setLevel(logging.INFO)
train_logger = logging.getLogger('query_module.train')
train_logger.setLevel(logging.INFO)
response_module_logger = logging.getLogger('response_module.ResponseModule')
response_module_logger.setLevel(logging.INFO)
database_logger = logging.getLogger('database.DataBaseManager')
database_logger.setLevel(logging.INFO)
management_logger = logging.getLogger('management_module.ManagementModule')
management_logger.setLevel(logging.INFO)
authentication_db_logger = logging.getLogger('authentication.db')
authentication_db_logger.setLevel(logging.DEBUG)
authentication_security_logger = logging.getLogger('authentication.security')
authentication_security_logger.setLevel(logging.DEBUG)

"""
    Flask configuration setup
"""
app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max size
ALLOWED_EXTENSIONS = set(['txt'])  # We only allow .txt files to be uploaded


@app.after_request
def after_request(resp):
    resp.headers["Access-Control-Allow-Origin"] = '*'
    request_headers = request.headers.get("Access-Control-Request-Headers")
    resp.headers["Access-Control-Allow-Headers"] = request_headers
    resp.headers['Access-Control-Allow-Methods'] = "DELETE, GET, POST, HEAD, OPTIONS"
    return resp


"""
    Path setup
"""
PATH = os.path.dirname(os.path.realpath(__file__))
INTENT_PATH = os.path.join(PATH, 'query_module/training_data/intents/')
ENTITY_PATH = os.path.join(PATH, 'query_module/training_data/entities/')
TEMP_PATH = os.path.join(PATH, 'management_module/temp/')


@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    if not username or not password:
        return jsonify(message=AuthenticationError.INVALID_CREDENTIALS.value), 401
    if authenticator.check_is_admin(username, password):
        return jsonify(token=generate_token('admin', username), id=username, authority='admin'), 200
    if authenticator.check_is_student(username, password):
        return jsonify(token=generate_token('student', username), id=username, authority='student'), 200
    logger.info('{}: {} login success'.format(username, password))
    return jsonify(message=AuthenticationError.INVALID_CREDENTIALS.value), 401


@app.route('/validation', methods=['POST'])
def validation():
    token = request.headers.get('authorization', None)
    if not token:
        return jsonify(message=AuthenticationError.INVALID_CREDENTIALS.value), 401
    verified = verify_token(token)
    if not verified:
        return jsonify(message=AuthenticationError.INVALID_CREDENTIALS.value), 401
    logger.info('{}: {} re-authenticated'.format(verified['user_id'], verified['user_type']))
    return jsonify(token=token, id=verified['user_id'], authority=verified['user_type']), 200


@app.route('/upload', methods=['POST'])
def upload():
    def allowed_file(f):
        return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    if 'file' not in request.files:
        return jsonify(message=UploadFileError.NO_FILE.value), 400
    file = request.files['file']
    if not file.filename:
        return jsonify(message=UploadFileError.NO_FILE_SELECTED.value), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(TEMP_PATH, "{}-{}.txt".format(filename.rstrip('.txt'), int(time.time())))
        file.save(file_path)
        if not management_module.train(file_path):
            os.remove(file_path)
            return jsonify(message=UploadFileError.INVALID_FORMAT.value), 400
        return jsonify(message=UploadFileSuccess.SUCCESS.value), 200


@app.route('/message', methods=['POST'])
def message():
    message = request.json.get('inputValue', None)
    username = request.json.get('username', None)
    id = request.json.get('id', None)

    query_result = query_module.query(message)
    return_message = response_module.respond(query_result)

    response = {
        'message': return_message,
        'timestamp': datetime.now(),
        'id': id
    }
    return jsonify(response), 200


if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=9999)

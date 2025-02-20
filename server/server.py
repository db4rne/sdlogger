from flask import Flask, request, jsonify, abort
from werkzeug.utils import secure_filename

from datetime import datetime
import uuid
import sys
import os


# client require to have Access-Token set to this
SECRET = "Ti0TahcaiN0Ahkeb1eegaiv6gu"

# storage path
STORAGE = "/srv/sdlogger/upload"
STORAGE = "/tmp/sdlogger"

# 20 mb
MAX_CONTENT_LENGTH = 20 * 1024 * 1024

use_redis = False
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

@app.route("/", methods=['GET', 'POST'])
def root():
    return "sdlogger uploader"

@app.route("/upload/<path:filename>", methods=['POST'])
def upload_file(filename):
    try:
        token = request.headers.get('Access-Token')
        if token != SECRET:
            abort(403)
    except:
        abort(403)

    filename = secure_filename(filename)
    prefix = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    prefix += '_' + str(uuid.uuid1())
    filename = prefix + '_' + filename
    fullpath = os.path.join(STORAGE, filename)

    with open(fullpath, 'wb') as file:
        chunk_size = 1024
        while True:
            chunk = request.stream.read(chunk_size)
            if len(chunk) == 0:
                break
            file.write(chunk)

    return jsonify({})

if __name__ == '__main__':
    host = "192.168.133.197"
    port = 80

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    # TODO: check if STORAGE is available and writeable
    app.run(host=host, port=port)

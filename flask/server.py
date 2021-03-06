#!/usr/bin/env python

# http://flask.pocoo.org/docs/deploying/wsgi-standalone/

import os
import os.path
import sys
import re
import logging
import tempfile
import subprocess
import flask
from flask_cors import cross_origin 
from werkzeug import secure_filename

logging.basicConfig(level=logging.INFO)

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'JPG', 'gif'])

app = flask.Flask(__name__)

# http://flask.pocoo.org/docs/api/#configuration
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024
app.config['TESSERACT']  = '/usr/bin/tesseract'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
@cross_origin(methods=['POST'])
def upload_file():

    if flask.request.method == 'GET':
        return flask.render_template("index.html")

    # http://flask.pocoo.org/docs/patterns/fileuploads/

    try:
        file = flask.request.files['file']
    except Exception, e:
        logging.error(e)
        flask.abort(400)

    if not file:
        logging.error("Missing file")
        flask.abort(404)

    filename = secure_filename(file.filename)
    
    if not allowed_file(filename):
        logging.error("Invalid file")
        flask.abort(406)

    # Now we rewrite the filename

    fname, ext = os.path.splitext(filename)
    pid = os.getpid()

    fname = "%s-%s" % (pid, fname)
    filename = fname + ext
    
    tmpdir = tempfile.gettempdir()
    image = os.path.join(tmpdir, filename)

    logging.debug("image to process is %s" % image)

    try:
        file.save(image)
    except Exception, e:
        logging.error("Failed to save file: %s" % e)
        flask.abort(500)

    try:
        subprocess.call([app.config['TESSERACT'], image, fname])
    except Exception, e:
        logging.error(e)
        flask.abort(500)

    output = "%s.txt" % fname

    if not os.path.exists(output):
        logging.error("expected output file '%s' does not exist" % output)
        flask.abort(500)

    # rsp = flask.send_file(output)

    fh = open(output, 'r')
    raw = fh.read()
    fh.close()

    # See this? It is the "simplest and dumbest" solution. Which is fancy-talk
    # for incomplete. It doesn't even capture all the accession numbers in the
    # Cooper-Hewitt's collection. See also:
    #
    # One important thing to note is that while accession numbers are pretty
    # straightforward there are variations and the code as it written today
    # does not account for them. If nothing else we hope that by releasing the
    # source code we can use it as a place to capture and preserve a catalog of
    # patterns because life is too short to spend very much of it training robot
    # eyes to recognize accession numbers.
    #
    # http://labs.cooperhewitt.org/2014/label-whisperer/

    raw = raw.strip()
    match = re.findall(r'.*?((?:[a-z0-9]+)-(?:[a-z0-9]+)-(?:[a-z0-9]+)).*?', raw)

    rsp = flask.jsonify(raw=raw, possible=match)

    os.unlink(image)
    os.unlink(output)

    return rsp

if __name__ == '__main__':
    debug = False	# sudo make me a CLI option
    app.run(debug=debug)

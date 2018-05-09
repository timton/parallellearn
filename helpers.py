import csv
import urllib.request

from flask import redirect, render_template, request, session, url_for
from functools import wraps

SUPPORTED_TYPES = ["book", "movie", "series", "song"]
ALLOWED_FILE_EXTENSIONS = set(['xls', 'xlsx', 'xlsm', 'xltx', 'xltm'])

# https://stackoverflow.com/questions/2336522/png-vs-gif-vs-jpeg-vs-svg-when-best-to-use
ALLOWED_POSTER_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'svg'])
SUPPORTED_LANGUAGES = [
        'afrikanns', 'albanian', 'arabic', 'armenian', 'basque', 'bengali',
        'bulgarian', 'catalan', 'cambodian', 'chinese', 'croation', 'czech',
        'danish', 'dutch', 'english', 'estonian', 'fiji', 'finnish', 'french',
        'georgian', 'german', 'greek', 'gujarati', 'hebrew', 'hindi',
        'hungarian', 'icelandic', 'indonesian', 'irish', 'italian', 'japanese',
        'javanese', 'korean', 'latin', 'latvian', 'lithuanian', 'macedonian',
        'malay', 'malayalam', 'maltese', 'maori', 'marathi', 'mongolian', 'nepali',
        'norwegian', 'persian', 'polish', 'portuguese', 'punjabi', 'quechua',
        'romanian', 'russian', 'samoan', 'serbian', 'slovak', 'slovenian',
        'spanish', 'swahili', 'swedish', 'tamil', 'tatar', 'telugu', 'thai',
        'tibetan', 'tonga', 'turkish', 'ukranian', 'urdu', 'uzbek', 'vietnamese',
        'welsh', 'xhosa'
    ]

# ensure selected file allowed
# extension must present and allowed
def forbidden_file(filename):
    return '.' not in filename or \
           filename.rsplit('.', 1)[1].lower() not in ALLOWED_FILE_EXTENSIONS

# ensure selected poster image allowed
# extension must present and allowed
def forbidden_poster(filename):
    return '.' not in filename or \
           filename.rsplit('.', 1)[1].lower() not in ALLOWED_POSTER_EXTENSIONS


def apology(error_message="", error_cause=""):
    """Renders message as an apology to user."""

    return render_template("apology.html", error_message=error_message, error_cause=error_cause)

def success(success_message=""):
    """Renders message as a confirmation of a successful action."""

    return render_template("success.html", success_message=success_message)

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.11/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("log_in", next=request.url))
        return f(*args, **kwargs)
    return decorated_function
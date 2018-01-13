import csv
import urllib.request

from flask import redirect, render_template, request, session, url_for
from functools import wraps

SUPPORTED_TYPES = ["book", "movie", "tv series", "song"]
ALLOWED_EXTENSIONS = set(['xls', 'xlsx', 'xlsm', 'xltx', 'xltm', 'txt'])
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
           filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS

def apology(top="", bottom=""):
    """Renders message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
            ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=escape(top), bottom=escape(bottom))

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

def lookup(symbol):
    """Look up quote for symbol."""

    # reject symbol if it starts with caret
    if symbol.startswith("^"):
        return None

    # reject symbol if it contains comma
    if "," in symbol:
        return None

    # query Yahoo for quote
    # http://stackoverflow.com/a/21351911
    try:
        url = "http://download.finance.yahoo.com/d/quotes.csv?f=snl1&s={}".format(symbol)
        webpage = urllib.request.urlopen(url)
        datareader = csv.reader(webpage.read().decode("utf-8").splitlines())
        row = next(datareader)
    except:
        return None

    # ensure stock exists
    try:
        price = float(row[2])
    except:
        return None

    # return stock's name (as a str), price (as a float), and (uppercased) symbol (as a str)
    return {
        "name": row[1],
        "price": price,
        "symbol": row[0].upper()
    }

def usd(value):
    """Formats value as USD."""
    return "${:,.2f}".format(value)

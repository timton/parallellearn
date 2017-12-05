from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from time import gmtime, strftime

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///parallellearn.db")

# main page route
@app.route("/")
def index():

    # get the 5 newest projects
    # https://stackoverflow.com/questions/14018394/android-sqlite-query-getting-latest-10-records
    new_projects = db.execute("SELECT * FROM (SELECT * FROM projects ORDER BY timestamp ASC LIMIT 5) \
                              ORDER BY timestamp DESC")

    # get the 5 most popular projects
    popular_projects = db.execute("SELECT * FROM (SELECT * FROM projects ORDER BY rating ASC LIMIT 5) \
                              ORDER BY rating DESC")

    # render the user's home page, passing in his data
    return render_template("index.html", new_projects=new_projects, popular_projects=popular_projects)

# register route
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure email was submitted
        if not request.form.get("email"):
            return apology("must provide email")

        # ensure username was submitted
        elif not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # ensure password was confirmed
        elif not request.form.get("confirm_password"):
            return apology("must confirm password")

        # ensure passwords match
        elif not request.form.get("password") == request.form.get("confirm_password"):
            return apology("passwords do not match")

        # ensure email uniqueness
        row = db.execute("SELECT * FROM users WHERE email = :email",
                         email=request.form.get("email"))
        if row:
            return apology("try another email")

        # ensure username uniqueness
        row = db.execute("SELECT * FROM users WHERE username = :username",
                         username=request.form.get("username"))
        if row:
            return apology("try another username")

        # try to register new user
        try:
            key = db.execute("INSERT INTO users (email, username, hash) VALUES(:email, :username, :hash)",
                             email=request.form.get("email"),
                             username=request.form.get("username"),
                             hash=pwd_context.hash(request.form.get("password")))
        except RuntimeError:
            return apology("error while performing registration")


        # once successfully registered, log user in automatically
        session["user_id"] = key

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")



######################
# DONE UP UNTIL HERE #
######################


@app.route("/browse")
def browse():
    return

@app.route("/faq")
def faq():
    return

@app.route("/about")
def about():
    return

@app.route("/contact")
def contact():
    return

@app.route("/download")
def download():
    return

@app.route("/upload")
@login_required
def upload():
    return

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure stock symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide stock symbol")

        # ensure number of shares was submitted
        if not request.form.get("shares"):
            return apology("must provide number of shares to buy")

        # ensure number of shares was submitted
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("must provide a number of shares")

        # ensure valid number of shares was submitted
        if shares <= 0:
            return apology("must provide a valid number of shares")

        # look up stock
        stock = lookup(request.form.get("symbol"))

        # ensure valid stock
        if stock == None:
            return apology("must provide valid stock")

        # get user's cash
        rows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
        cash = rows[0]["cash"]

        # insufficient cash scenario
        stock_value = shares * stock["price"]
        if stock_value > cash:
            return apology("not enough cash")

        # if enough money, update user's portfolio, ...
        rows = db.execute("SELECT * FROM portfolios WHERE user_id = :user_id AND stock = :stock",
                          user_id=session["user_id"], stock=stock["symbol"])
        if len(rows) == 1:
            db.execute("UPDATE portfolios SET shares = shares + :shares WHERE id = :id",
                       shares=shares, id=rows[0]["id"])
        else:
            db.execute("INSERT INTO portfolios (user_id, stock, shares) VALUES(:user_id, :stock, :shares)",
                       user_id=session["user_id"], stock=stock["symbol"], shares=shares)

        # ... update user's cash amount, ...
        db.execute("UPDATE users SET cash = cash - :stock_value WHERE id = :id",
                   stock_value=stock_value, id=session["user_id"])

        # ..., log the transaction, ...
        # timestamp format https://stackoverflow.com/questions/415511/how-to-get-current-time-in-python
        db.execute("INSERT INTO transactions (user_id, stock, shares, type, time, price) \
                                       VALUES(:user_id, :stock, :shares, :type, :time, :price)",
                    user_id=session["user_id"], stock=stock["symbol"], shares=shares,
                    type="BUY", time=strftime("%H:%M:%S %Y-%m-%d", gmtime()), price=stock_value)

        # ... and redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions."""

    # fetch user's transactions, latest first
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = :user_id ORDER BY time DESC",
                              user_id=session["user_id"])

    # render the history template
    return render_template("history.html", transactions=transactions)

@app.route("/log_in", methods=["GET", "POST"])
def log_in():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/log_out")
def log_out():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure stock symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide stock symbol")

        # look up stock
        stock = lookup(request.form.get("symbol"))

        # ensure valid stock
        if stock == None:
            return apology("must provide valid stock")

        # if stock valid, display it
        return render_template("quoted.html", stock=stock)

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure stock symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide stock symbol")

        # fetch the stock to sell
        rows = db.execute("SELECT * FROM portfolios WHERE user_id = :user_id AND stock = :stock",
                          user_id=session["user_id"], stock=request.form.get("symbol"))
        stock = rows[0]

        # get stock's current value
        stock_update = lookup(request.form.get("symbol"))
        stock_value = stock["shares"] * stock_update["price"]

        # update user's cash amount
        db.execute("UPDATE users SET cash = cash + :stock_value WHERE id = :id",
                   stock_value=stock_value, id=session["user_id"])

        # delete stock from user's portfolio
        rows = db.execute("DELETE FROM portfolios WHERE user_id = :user_id AND stock = :stock",
                          user_id=session["user_id"], stock=stock["stock"])

        # log the transaction
        # timestamp format https://stackoverflow.com/questions/415511/how-to-get-current-time-in-python
        db.execute("INSERT INTO transactions (user_id, stock, shares, type, time, price) \
                                       VALUES(:user_id, :stock, :shares, :type, :time, :price)",
                    user_id=session["user_id"], stock=stock["stock"], shares=stock["shares"],
                    type="SELL", time=strftime("%H:%M:%S %Y-%m-%d", gmtime()), price=stock_value)

        # ... and redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:

        # get the current user's stocks ...
        stocks = db.execute("SELECT * FROM portfolios WHERE user_id = :user_id", user_id=session["user_id"])

        # ... and render the selling interface
        return render_template("sell.html", stocks=stocks)

@app.route("/mamange_account", methods=["GET", "POST"])
def manage_account():
    """Change password."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure old password was submitted
        if not request.form.get("old_password"):
            return apology("must provide current password")

        # ensure new password was submitted
        elif not request.form.get("new_password"):
            return apology("must provide new password")

        # ensure new password was confirmed
        elif not request.form.get("confirm_password"):
            return apology("must confirm new password")

        # ensure old password is correct
        rows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
        if not pwd_context.verify(request.form.get("old_password"), rows[0]["hash"]):
            return apology("current password incorrect")

        # ensure new password is input twice
        elif request.form.get("new_password") != request.form.get("confirm_password"):
            return apology("new password must be input twice")

        # insure new password is different from the old one
        if pwd_context.verify(request.form.get("new_password"), rows[0]["hash"]):
            return apology("new password must be different from current one")

        # update new password hash
        db.execute("UPDATE users SET hash = :hash WHERE id = :id",
                   hash=pwd_context.hash(request.form.get("new_password")), id=session["user_id"])

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("account.html")
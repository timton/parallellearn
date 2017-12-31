from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from time import gmtime, strftime

# for file uploading
import os
from werkzeug.utils import secure_filename

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

# uploading files
# http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
UPLOAD_FOLDER = 'projects/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///parallellearn.db")

# main page route
@app.route("/")
def index():

    # get the newest versions
    new_versions = db.execute("SELECT * FROM versions ORDER BY timestamp DESC")
    new_projects = []

    if len(new_versions) > 0:

        # get only distinct projects
        different_projects = []
        for version in new_versions:
            if version["project_id"] not in different_projects:
                different_projects.append(version["project_id"])
            else:
                continue

        # get the newest 10 different projects
        for id in different_projects:
            rows = db.execute("SELECT * FROM projects WHERE id = :id", id=id)
            new_projects.append(rows[0])
        new_projects = new_projects[:10]

        # get all the metadata
        for project in new_projects:
            projects = db.execute("SELECT * FROM projects WHERE id = :id", id=project["id"])
            project["type"] = projects[0]["type"]
            project["title"] = projects[0]["title"]
            project["author"] = projects[0]["author"]
            project["year"] = projects[0]["year"]


            # get project languages
            rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id",
                              project_id=project["id"])
            languages = ""
            for row in rows:
                languages += (row["language"] + ", ")
            languages = languages[:-2]
            project["languages"] = languages

    # get the 5 most popular language versions
    popular_versions = db.execute("SELECT * FROM (SELECT * FROM versions ORDER BY rating ASC LIMIT 10) \
                              ORDER BY rating DESC")

    # get all the metadata
    if len(popular_versions) > 0:
        for version in popular_versions:
            projects = db.execute("SELECT * FROM projects WHERE id = :id", id=version["project_id"])
            version["type"] = projects[0]["type"]
            version["title"] = projects[0]["title"]
            version["author"] = projects[0]["author"]
            version["year"] = projects[0]["year"]

    # render the home page, passing in the data
    return render_template("index.html", new_projects=new_projects, popular_versions=popular_versions)

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

# logout route
@app.route("/log_out")
def log_out():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to welcome page
    return redirect(url_for("index"))

#login route
@app.route("/log_in", methods=["GET", "POST"])
def log_in():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure email/username was submitted
        if not request.form.get("email_or_username"):
            return apology("must provide email or username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for email or username
        rows = db.execute("SELECT * FROM users WHERE email = :email_or_username OR username = :email_or_username",
                          email_or_username=request.form.get("email_or_username"))

        # ensure email/username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid email/username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

# view account details route
@app.route("/view_details")
@login_required
def view_details():

    # fetch the user
    user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])

    return render_template("account_details.html", user=user[0])

# change password route
@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():

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
        return render_template("change_password.html")

# change email route
@app.route("/change_email", methods=["GET", "POST"])
@login_required
def change_email():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure new email was submitted
        if not request.form.get("new_email"):
            return apology("must provide new email")

        # ensure new email is different from the current one
        user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])

        if request.form.get("new_email") == user[0]["email"]:
            return apology("new email must be different from current one")

        # ensure email not already registered
        row = db.execute("SELECT * FROM users WHERE email = :email",
                         email=request.form.get("new_email"))
        if row:
            return apology("try another email")

        # update new email
        db.execute("UPDATE users SET email = :email WHERE id = :id",
                   email=request.form.get("new_email"), id=session["user_id"])

        # redirect user to home page
        return redirect(url_for("view_details"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("change_email.html")

# change username route
@app.route("/change_username", methods=["GET", "POST"])
@login_required
def change_username():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure new username was submitted
        if not request.form.get("new_username"):
            return apology("must provide new username")

        # ensure new username is different from the current one
        user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])

        if request.form.get("new_username") == user[0]["username"]:
            return apology("new username must be different from current one")

        # ensure username not already registered
        row = db.execute("SELECT * FROM users WHERE username = :username",
                         username=request.form.get("new_username"))
        if row:
            return apology("try another username")

        # update new username
        db.execute("UPDATE users SET username = :username WHERE id = :id",
                   username=request.form.get("new_username"), id=session["user_id"])

        # redirect user to home page
        return redirect(url_for("view_details"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("change_username.html")

@app.route("/upload_new", methods=["GET", "POST"])
@login_required
def upload_new():
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure type submitted and ...
        if not request.form.get("type"):
            return apology("must provide the type of this project")
        else:
            type = request.form.get("type").lower()

        # ... ensure supported type submitted
        if type not in SUPPORTED_TYPES:
            return apology("must provide correct type: book, movie, tv series, or song")

        # ensure title of the project was submitted
        if not request.form.get("title"):
            return apology("must provide title for this project")
        else:
            title = request.form.get("title").lower()

        # ensure author of the project was submitted
        if not request.form.get("author"):
            return apology("must provide author's name for this project")
        else:
            author = request.form.get("author").lower()

        # ensure year of the project was submitted
        if not request.form.get("year"):
            return apology("must provide year for this project")
        else:
            year = request.form.get("year")

        # ensure number of language versions submitted
        if not request.form.get("number_of_versions"):
            return apology("must provide number of language versions for this project")
        else:
            number_of_versions = int(request.form.get("number_of_versions"))

        # ensure supported languages submitted
        for i in range(number_of_versions):
            if not request.form.get("language_version" + str(i + 1)):
                return apology("must provide languages for this project")
            if request.form.get("language_version" + str(i + 1)).lower() not in SUPPORTED_LANGUAGES:
                return apology("must submit project in supported languages (better select)")


        # ENSURE FILE SELECTED FOR UPLOAD
        # http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
        # check if the post request has the file part
        if 'file' not in request.files:
            return apology("must select file to upload")

        # if user does not select file, browser also
        # submit a empty part without filename
        file = request.files['file']
        if not file or file.filename == '':
            return apology("no selected file")

        # ensure file name (extension) allowed
        if allowed_file(file.filename):
            return apology("must select .xls or .xlsx file")

        # try to upload new project metadata
        # get the project id if successful
        try:
            db.execute("INSERT INTO projects (type, title, author, year) \
                       VALUES(:type, :title, :author, :year)",
                       type=type, title=title, author=author, year=year)
            rows = db.execute("SELECT * FROM projects WHERE title = :title", title=title)
            project_id=rows[0]["id"]
        except RuntimeError:
            return apology("error while uploading new project metadata")


        # prepare to upload file (create name)
        project_languages = " ("
        for i in range(number_of_versions):
            project_languages += (request.form.get("language_version" + str(i + 1)).lower() + ", ")
        project_languages = project_languages[:-2]
        project_languages += ")"
        filename = title + " - " + author + " - " + str(year) + project_languages + "." + \
                       file.filename.rsplit('.', 1)[1].lower()

        # try to upload the file
        try:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        except RuntimeError:
            return apology("couldn't upload te selected file")

        # try to upload new project language versions
        for i in range(number_of_versions):
            try:
                key2 = db.execute("INSERT INTO versions (project_id, user_id, language, timestamp, filepath, column_number) \
                                 VALUES(:project_id, :user_id, :language, :timestamp, :filepath, :column_number)",
                                 project_id=project_id, user_id=session["user_id"],
                                 language=request.form.get("language_version" + str(i + 1)).lower(),
                                 timestamp=strftime("%H:%M:%S %Y-%m-%d", gmtime()),
                                 filepath=UPLOAD_FOLDER+filename,
                                 column_number=(i + 1))
            except RuntimeError:
                return apology("error while uploading new project language version")

        # once successful, back to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("upload_new.html")


@app.route("/upload_existing", methods=["GET", "POST"])
@login_required
def upload_existing():

    # query for all the existing projects
    existing_projects = db.execute("SELECT * FROM projects")

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure project submitted and ...
        if not request.form.get("project"):
            return apology("must choose project to update")
        else:
            project_name = request.form.get("project").lower()

        # ... ensure project exists
        project_id = -1
        for project in existing_projects:
            name = "[" + project["type"] + "] " + project["title"] + " - " + project["author"] + " (" + str(project["year"]) + ")"
            if name == project_name:
                project_id = project["id"]
                break
        if project_id == -1:
            return apology("must choose among existing projects")

        # ensure number of language versions submitted
        if not request.form.get("number_of_versions"):
            return apology("must provide number of language versions for this project")
        else:
            number_of_versions = int(request.form.get("number_of_versions"))

        # ensure supported language(s) submitted
        for i in range(number_of_versions):
            if not request.form.get("language_version" + str(i + 1)):
                return apology("must provide languages for this project")
            if request.form.get("language_version" + str(i + 1)).lower() not in SUPPORTED_LANGUAGES:
                return apology("must submit project in supported languages (better select)")


        # ENSURE FILE SELECTED FOR UPLOAD
        # http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
        # check if the post request has the file part
        if 'file' not in request.files:
            return apology("must select file to upload")

        # if user does not select file, browser also
        # submit a empty part without filename
        file = request.files['file']
        if not file or file.filename == '':
            return apology("no selected file")

        # ensure file name (extension) allowed
        if allowed_file(file.filename):
            return apology("must select .xls or .xlsx file")

        # get project metadata
        rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
        project = rows[0]

        # prepare to upload file (create name)
        project_languages = " ("
        for i in range(number_of_versions):
            project_languages += (request.form.get("language_version" + str(i + 1)).lower() + ", ")
        project_languages = project_languages[:-2]
        project_languages += ")"
        filename = project["title"] + " - " + project["author"] + " - " + str(project["year"]) + \
                   project_languages + "." + file.filename.rsplit('.', 1)[1].lower()

        # try to upload the file
        try:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        except RuntimeError:
            return apology("couldn't upload te selected file")

        # try to upload new project language versions
        for i in range(number_of_versions):
            try:
                key2 = db.execute("INSERT INTO versions (project_id, user_id, language, timestamp, filepath, column_number) \
                                 VALUES(:project_id, :user_id, :language, :timestamp, :filepath, :column_number)",
                                 project_id=project_id, user_id=session["user_id"],
                                 language=request.form.get("language_version" + str(i + 1)).lower(),
                                 timestamp=strftime("%H:%M:%S %Y-%m-%d", gmtime()),
                                 filepath=UPLOAD_FOLDER+filename,
                                 column_number=(i + 1))
            except RuntimeError:
                return apology("error while uploading new project language version")

        # once successful, back to home page
        return redirect(url_for("index"))


    # else if user reached route via GET (as by clicking a link or via redirect)
    else:

        # return the list of projects for the user to choose from
        return render_template("upload_existing.html", existing_projects=existing_projects)


# route with parameters
# https://stackoverflow.com/questions/14032066/can-flask-have-optional-url-parameters
# display project info
@app.route("/view_project/<title>")
def view_project(title):

    # get project metadata
    rows = db.execute("SELECT * FROM projects WHERE title = :title", title=title)
    project = rows[0]

    # get project languages
    rows = db.execute("SELECT * FROM versions WHERE project_id = :id", id=project["id"])
    languages = ""
    for row in rows:
        languages += (row["language"] + ", ")
    languages = languages[:-2]
    project["languages"] = languages

    return render_template("view_project.html", project=project)


# view account history route
@app.route("/view_history")
@login_required
def view_history():

    # get user's started projects
    started_projects = db.execute("SELECT * FROM history WHERE user_id = :user_id",
                                  user_id=session["user_id"])

    # get all the metadata
    if len(started_projects) > 0:
        for project in started_projects:

            # add "from_version" metadata
            rows = db.execute("SELECT * FROM versions WHERE id = :id", id=project["from_version_id"])
            project["from_language"] = rows[0]["from_version_id"]

            # add "to_version" metadata
            rows = db.execute("SELECT * FROM versions WHERE id = :id", id=project["to_version_id"])
            project["to_language"] = rows[0]["to_version_id"]

            # add project metadata
            rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project["project_id"])
            project["type"] = rows[0]["type"]
            project["title"] = rows[0]["title"]
            project["author"] = rows[0]["author"]
            project["year"] = rows[0]["year"]


    # get user's uploaded versions
    uploaded_versions = db.execute("SELECT * FROM versions WHERE user_id = :user_id",
                                   user_id=session["user_id"])
    different_projects = []

    if len(uploaded_versions) > 0:

        # get only distinct files
        different_files = []
        for version in uploaded_versions:
            if version["filepath"] not in different_files:
                different_files.append(version["filepath"])

        different_projects = []
        for file in different_files:
            project = {}
            project["filepath"] = file
            languages = ""
            for version in uploaded_versions:
                if version["filepath"] == file:
                    project["id"] = version["project_id"]
                    languages += (version["language"] + ", ")
            languages = languages[:-2]
            project["languages"] = languages
            different_projects.append(project)


        # get projects' metadata
        for project in different_projects:
            rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project["id"])
            project["type"] = rows[0]["type"]
            project["title"] = rows[0]["title"]
            project["author"] = rows[0]["author"]
            project["year"] = rows[0]["year"]


    # render the account history page, passing in the data
    return render_template("account_history.html",
                           started_projects=started_projects, uploaded_projects=different_projects)


# delete uploaded project route
@app.route("/delete_project", methods=["GET", "POST"])
@login_required
def delete_project():

    # if delete button pressed
    # get submit button values
    # https://stackoverflow.com/questions/19794695/flask-python-buttons
    # Flask button passing variable back to python
    # https://stackoverflow.com/questions/41026510/flask-button-passing-variable-back-to-python
    if request.method == "POST":

        file_to_delete = request.form['delete_project']

        # save the project metadata first (for project deletion purposes afterwards)
        rows = db.execute("SELECT * FROM versions WHERE filepath = :filepath",
                          filepath=file_to_delete)
        version = rows[0]

        # delete the project
        try:
            db.execute("DELETE FROM 'versions' WHERE filepath = :filepath",
                       filepath=file_to_delete)
        except RuntimeError:
            return apology("couldn't delete this project")

        # delete the file as well
        try:
            os.remove(file_to_delete)
        except RuntimeError:
            return apology("couldn't delete this project")

        # check whether we have any more versions of the same project
        rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id",
                          project_id=version['project_id'])

        # if no more versions of the same project, delete project metadata as well
        if len(rows) == 0:
            try:
                db.execute("DELETE FROM 'projects' WHERE id = :id", id=version['project_id'])
            except RuntimeError:
                return apology("couldn't delete this project")

    # back to account history after deletion
    return view_history()


















######################
# DONE UP UNTIL HERE #
######################



















# change account history route
@app.route("/change_history", methods=["GET", "POST"])
def change_history():
    return

    """
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
        return render_template("my_account.html")
    """



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
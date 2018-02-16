from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from time import gmtime, strftime
from random import shuffle

# for file uploading, manipulation
import os
from werkzeug.utils import secure_filename

# for excel manipulation
import openpyxl

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

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# uploading files
# http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
UPLOAD_FOLDER = 'static/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///parallellearn.db")

# main page route
@app.route("/")
def index():

    # get all the supported languages
    all_versions = db.execute("SELECT * FROM versions")
    possible_languages = []
    for version in all_versions:
        if version["language"] not in possible_languages:
            possible_languages.append(version["language"])
    possible_from_languages = sorted(possible_languages)

    # https://stackoverflow.com/questions/4183506/python-list-sort-in-descending-order
    possible_to_languages = sorted(possible_languages, reverse=True)

    # get the newest versions
    new_versions = db.execute("SELECT * FROM versions ORDER BY timestamp DESC")
    new_projects = []

    if len(new_versions) > 0:

        # get the first 10 distinct projects IDs
        different_projects = []
        for version in new_versions:
            if version["project_id"] not in different_projects:
                different_projects.append(version["project_id"])
                if len(different_projects) == 10:
                    break
            else:
                continue

        # get the newest 10 different projects
        for id in different_projects:
            rows = db.execute("SELECT * FROM projects WHERE id = :id", id=id)
            new_projects.append(rows[0])

        # get all the displayable metadata
        for project in new_projects:

            # if tv series, make title include the season & episode
            if project["type"].lower() == "tv series":
                project["title"] += (" (s" + str(project["season"]) + "/e" + str(project["episode"]) +")")

            # get project languages
            rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id",
                              project_id=project["id"])

            languages_list = []
            for row in rows:
                if row["language"] not in languages_list:
                    languages_list.append(row["language"])
            languages_list = sorted(languages_list)

            languages_string = ""
            for language in languages_list:
                languages_string += (language + ", ")

            languages_string = languages_string[:-2]
            project["languages"] = languages_string

    # get the 5 most popular language versions
    popular_versions = db.execute("SELECT * FROM versions ORDER BY rating DESC LIMIT 10")

    # get all the metadata
    if len(popular_versions) > 0:
        for version in popular_versions:
            projects = db.execute("SELECT * FROM projects WHERE id = :id", id=version["project_id"])
            version["type"] = projects[0]["type"]
            version["title"] = projects[0]["title"]

            # if tv series, make title include the season & episode
            if version["type"].lower() == "tv series":
                version["title"] += (" (s" + str(projects[0]["season"]) + "/e" + str(projects[0]["episode"]) +")")

            version["author"] = projects[0]["author"]
            version["year"] = projects[0]["year"]

    # render the home page, passing in the data
    return render_template("index.html", possible_from_languages=possible_from_languages,
                           possible_to_languages=possible_to_languages, new_projects=new_projects,
                           popular_versions=popular_versions)


# prepare quick practice route
@app.route("/quick_practice", methods=["GET", "POST"])
def quick_practice():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # get the desired practice languages
        from_language = request.form.get("from_language").lower()
        to_language = request.form.get("to_language").lower()

        # ensure different languages
        if from_language == to_language:
            return apology("Couldn't load the practice interface.", "Must select different practice languages.")

        # get all the projects that support the 'from language'
        from_projects = []
        rows = db.execute("SELECT * FROM versions WHERE language = :language", language=from_language)
        for row in rows:
            from_projects.append(row["project_id"])
        from_projects = list(set(from_projects))

        # get all the projects that support both languages
        possible_projects = []
        for project_id in from_projects:
            rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id AND language = :language",
                              project_id=project_id, language=to_language)
            if len(rows) > 0:
                for row in rows:
                    possible_projects.append(row["project_id"])

        # make sure combination possible
        if len(possible_projects) == 0:
            x = "Sorry, this combination (from {f} to {t}) is not supported.".format(f=from_language, t=to_language)
            y = "Please try a different language combination. Thank you!"
            return apology(x, y)

        # get all the lines, to and from, separately
        # separately, because we might have different versions with the same language
        # all lines need corresponding mapping afterwards
        from_lines = []
        to_lines = []
        for project_id in possible_projects:

            # get the project, mostly for the line count
            rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
            project = rows[0]

            # get all the from versions
            from_versions = db.execute("SELECT * FROM versions WHERE project_id = :project_id AND language = :language",
                                       project_id=project_id, language=from_language)

            # iterate over the from versions
            for version in from_versions:

                rows = db.execute("SELECT * FROM lines WHERE version_id = :version_id", version_id=version["id"])

                # save each line as a tuple, with its project id, line index and string
                for row in rows:
                    x = (row["project_id"], row["line_index"], row["line"])
                    from_lines.append(x)

            # same with to versions
            to_versions = db.execute("SELECT * FROM versions WHERE project_id = :project_id AND language = :language",
                                     project_id=project_id, language=to_language)

            for version in to_versions:

                rows = db.execute("SELECT * FROM lines WHERE version_id = :version_id", version_id=version["id"])

                for row in rows:
                    x = (row["project_id"], row["line_index"], row["line"])
                    to_lines.append(x)

        # doing the mapping
        lines = []
        for from_line in from_lines:

            possible_to_lines = []

            # get the project id and line index
            i = from_line[0]
            j = from_line[1]

            # get all to lines with same index
            for to_line in to_lines:
                if to_line[0] == i and to_line[1] == j:
                    possible_to_lines.append(to_line[2])

            # random shuffle of to lines
            shuffle(possible_to_lines)

            # map the first
            x = (from_line[2], possible_to_lines[0])

            # append the line
            lines.append(x)

        # shuffle lines before rendering
        # https://stackoverflow.com/questions/976882/shuffling-a-list-of-objects
        shuffle(lines)

        # prepare lists to render
        from_lines = []
        to_lines = []
        for line in lines:
            from_lines.append(line[0])
            to_lines.append(line[1])

        # prepare project to render
        project = {}
        project["from_language"] = from_language
        project["to_language"] = to_language
        project["line_count"] = len(lines)

        return render_template("quick_practice.html", from_lines=from_lines, to_lines=to_lines, project=project)

    # else if user reached route via GET (as by clicking a link or via redirect)
    # go to index
    else:
        return index()


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

# upload new project - we start with the type
@app.route("/new_project_type", methods=["GET", "POST"])
@login_required
def new_project_type():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # get the new project type, store it in the new project object
        session["new_project"]["type"] = request.form.get("new_project_type").lower()

        return render_template("new_project_metadata.html")

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:

        # create a new project object
        session["new_project"] = {}

        # start the uploading process with the type template
        return render_template("new_project_type.html")


# upload new project - project metadata
@app.route("/new_project_metadata", methods=["GET", "POST"])
@login_required
def new_project_metadata():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # get the new project title, store it in the new project object
        # ensure title of the project was submitted
        if not request.form.get("new_project_title"):
            session.pop('new_project', None)
            return apology("Couldn't upload this project.", "Please provide a title.")
        else:
            session["new_project"]["title"] = request.form.get("new_project_title").lower()

        # for tv series, save the season and episode
        if session["new_project"]["type"].lower() == "tv series":
            if not request.form.get("new_project_season") or not request.form.get("new_project_episode"):
                session.pop('new_project', None)
                return apology("Couldn't upload this project.",
                               "Please provide a season and/or an episode number.")
            else:
                session["new_project"]["season"] = request.form.get("new_project_season")
                session["new_project"]["episode"] = request.form.get("new_project_episode")

        # get the new project author, store it in the new project object
        if not request.form.get("new_project_author"):
            session.pop('new_project', None)
            return apology("Couldn't upload this project.", "Please provide an author.")
        else:
            session["new_project"]["author"] = request.form.get("new_project_author").lower()

        # get the new project type, store it in the new project object
        if not request.form.get("new_project_year"):
            session.pop('new_project', None)
            return apology("Couldn't upload this project.", "Please provide a year.")
        else:
            session["new_project"]["year"] = request.form.get("new_project_year")

        # ENSURE FILE SELECTED FOR UPLOAD
        # http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
        # check if the post request has the file part
        if 'file' not in request.files:
            session.pop('new_project', None)
            return apology("Couldn't upload this project.", "Please select a file to upload.")

        # if user does not select file, browser also
        # submit a empty part without filename
        file = request.files['file']
        if not file or file.filename == '':
            session.pop('new_project', None)
            return apology("Couldn't upload this project.", "Please select a file to upload.")

        # ensure file name (extension) allowed
        if forbidden_file(file.filename):
            session.pop('new_project', None)
            return apology("Couldn't upload this project.",
                           "Allowed extensions: xls/xlsx/xlsm/xltx/xltm.")

        # make sure project doesn't exist already
        if session["new_project"]["type"].lower() == "tv series":
            rows = db.execute("SELECT * FROM projects WHERE type = :type AND title = :title AND author = :author AND \
                              year = :year AND season = :season AND episode = :episode",
                              type=session["new_project"]["type"].lower(), title=session["new_project"]["title"].lower(),
                              author=session["new_project"]["author"].lower(), year=session["new_project"]["year"],
                              season=session["new_project"]["season"], episode=session["new_project"]["episode"])
        else:
            rows = db.execute("SELECT * FROM projects WHERE type = :type AND title = :title AND author = :author AND year = :year",
                              type=session["new_project"]["type"].lower(), title=session["new_project"]["title"].lower(),
                              author=session["new_project"]["author"].lower(), year=session["new_project"]["year"])
        if len(rows) > 0:
            session.pop('new_project', None)
            return apology("This project already exists.", "Try simply uploading versions for it.")

        # ensure 2 <-> 5 language versions
        workbook = openpyxl.load_workbook(file)
        session["new_project"]["number_of_versions"] = len(workbook.worksheets)

        if session["new_project"]["number_of_versions"] > 5:
            session.pop('new_project', None)
            return apology("Couldn't upload this project.",
                           "Don't overwork - neither yourself, nor the server (maximum 5 language versions allowed per file).")
        elif session["new_project"]["number_of_versions"] < 2:
            session.pop('new_project', None)
            return apology("Couldn't upload this project.",
                           "A new project must have at least two language versions.")

        # make sure all versions have the same number of lines
        session["new_project"]["line_count"] = workbook.worksheets[0].max_row
        for worksheet in workbook:
            if worksheet.max_row != session["new_project"]["line_count"]:
                session.pop('new_project', None)
                return apology("Couldn't upload this project.",
                               "All language versions have to have the same number of lines.")

        # save all the lines
        # https://stackoverflow.com/questions/13377793/is-it-possible-to-get-an-excel-documents-row-count-without-loading-the-entire-d
        session["new_project"]["lines"] = []
        for worksheet in workbook:
            l = []
            for row in worksheet.iter_rows(min_row=1, max_col=1, max_row=session["new_project"]["line_count"]):
                for cell in row:
                    value = str(cell.value)
                    l.append(value)
            session["new_project"]["lines"].append(l)

        return render_template("new_project_versions.html")

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return new_project_type()


# upload new project - project versions
@app.route("/new_project_versions", methods=["GET", "POST"])
@login_required
def new_project_versions():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # save language versions
        session["new_project"]["versions"] = []
        for i in range(session["new_project"]["number_of_versions"]):
            session["new_project"]["versions"].append(request.form.get(str(i)).lower())

        # ensure at least two different language versions
        if len(set(session["new_project"]["versions"])) == 1:
            session.pop('new_project', None)
            return apology("Couldn't upload this project.",
                           "New project must have at least two different language versions.")

        return render_template("new_project_formatting.html")

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return new_project_type()

# upload new project - project poster and description
@app.route("/new_project_formatting", methods=["GET", "POST"])
@login_required
def new_project_formatting():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ENSURE POSTER SELECTED FOR UPLOAD
        # http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
        # check if the post request has the file part
        if 'poster' not in request.files:
            session.pop('new_project', None)
            return apology("Couldn't upload this project.", "Please select a poster image.")

        # if user does not select file, browser also
        # submit a empty part without filename
        file = request.files['poster']
        if not file or file.filename == '':
            session.pop('new_project', None)
            return apology("Couldn't upload this project.", "Please select a poster image.")

        # ensure poster file (extension) allowed
        if forbidden_poster(file.filename):
            session.pop('new_project', None)
            return apology("Couldn't upload this project.",
                           "Allowed extensions for poster images: jpeg/jpeg/png/svg.")

        # ensure poster image not too large
        # https://stackoverflow.com/questions/2104080/how-to-check-file-size-in-python
        old_file_position = file.tell()
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(old_file_position, os.SEEK_SET)
        if size > 307200:
            session.pop('new_project', None)
            return apology("Couldn't upload this project.", "Maximum size for poster images is 300 KB.")

        # get the new project description, store it in the new project object
        # ensure description of the project was submitted
        if not request.form.get("new_project_description"):
            session.pop('new_project', None)
            return apology("Couldn't upload this project.", "Please provide a description.")
        else:
            session["new_project"]["description"] = request.form.get("new_project_description")

        # make sure description not too long
        if len(session["new_project"]["description"]) > 1000:
            session.pop('new_project', None)
            return apology("Let's not go overboard.", "Description too long (maximum 1000 characters).")

        # try to upload the poster
        try:
            postername = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], postername))
        except RuntimeError:
            session.pop('new_project', None)
            return apology("Couldn't upload this project.", "Please try again later.")

        # upload new project metadata
        try:
            if session["new_project"]["type"] != "tv series":
                db.execute("INSERT INTO projects (type, title, author, year, user_id, line_count, poster, description) \
                           VALUES (:type, :title, :author, :year, :user_id, :line_count, :poster, :description)",
                           type=session["new_project"]["type"], title=session["new_project"]["title"],
                           author=session["new_project"]["author"], year=session["new_project"]["year"],
                           user_id=session["user_id"], line_count=session["new_project"]["line_count"],
                           poster=postername, description=session["new_project"]["description"])
            else:
                db.execute("INSERT INTO projects (type, title, author, year, user_id, line_count, season, episode, poster, description) \
                           VALUES (:type, :title, :author, :year, :user_id, :line_count, :season, :episode, :poster, :description)",
                           type=session["new_project"]["type"], title=session["new_project"]["title"],
                           author=session["new_project"]["author"], year=session["new_project"]["year"],
                           user_id=session["user_id"], line_count=session["new_project"]["line_count"],
                           season=session["new_project"]["season"], episode=session["new_project"]["episode"],
                           poster=postername, description=session["new_project"]["description"])

        except RuntimeError:
            session.pop('new_project', None)
            return apology("Couldn't save this project in the database.")

        # get the id of the new project
        rows = db.execute("SElECT * FROM projects WHERE user_id = :user_id ORDER BY id DESC", user_id=session["user_id"])
        session["new_project"]["project_id"]=rows[0]["id"]

        # upload new project language versions
        for i in range(session["new_project"]["number_of_versions"]):
            try:
                db.execute("INSERT INTO versions (project_id, user_id, language, timestamp) VALUES(:project_id, \
                           :user_id, :language, :timestamp)", project_id=session["new_project"]["project_id"],
                           user_id=session["user_id"], language=session["new_project"]["versions"][i],
                           timestamp=strftime("%H:%M:%S %Y-%m-%d", gmtime()))
            except RuntimeError:
                db.execute("DELETE FROM 'projects' WHERE id = :id", id=session["new_project"]["project_id"])
                db.execute("DELETE FROM 'versions' WHERE project_id = :project_id",
                           project_id=session["new_project"]["project_id"])
                session.pop('new_project', None)
                return apology("Couldn't save the language versions in the database.")

        # get the IDs of the new versions
        # https://stackoverflow.com/questions/10897339/python-fetch-first-10-results-from-a-list
        # https://stackoverflow.com/questions/3940128/how-can-i-reverse-a-list-in-python
        version_ids = []
        rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id ORDER BY id DESC",
                          project_id=session["new_project"]["project_id"])
        for row in rows:
            version_ids.append(row["id"])
        version_ids = version_ids[:session["new_project"]["number_of_versions"]]
        version_ids = list(reversed(version_ids))

        # upload the lines for each version
        # https://stackoverflow.com/questions/522563/accessing-the-index-in-python-for-loops
        for i in range(session["new_project"]["number_of_versions"]):
            for index, line in enumerate(session["new_project"]["lines"][i]):
                try:
                    db.execute("INSERT INTO lines (project_id, version_id, line_index, line) \
                               VALUES (:project_id, :version_id, :line_index, :line)",
                               project_id=session["new_project"]["project_id"],
                               version_id=version_ids[i], line_index=index, line=line)
                except RuntimeError:
                    for id in version_ids:
                        db.execute("DELETE FROM 'lines' WHERE version_id = :version_id", version_id=id)
                    db.execute("DELETE FROM 'projects' WHERE id = :id", id=session["new_project"]["project_id"])
                    db.execute("DELETE FROM 'versions' WHERE project_id = :project_id",
                               project_id=session["new_project"]["project_id"])
                    session.pop('new_project', None)
                    return apology("Couldn't save the lines in the database.")

        # if successful, pop the session variable and inform
        # personalize the message just to be kewl
        if session["new_project"]["type"].lower() == "tv series":
                session["new_project"]["title"] += (" (s" + str(session["new_project"]["season"]) + \
                                                    "/(e" + str(session["new_project"]["episode"]) +")")
        s = "\"" + session["new_project"]["title"].title() + "\"" + " by " + session["new_project"]["author"].title() + \
            " has been successfully uploaded."
        session.pop('new_project', None)

        return success(s)

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return new_project_type()

@app.route("/upload_existing", methods=["GET", "POST"])
@login_required
def upload_existing():

    # query for all the existing projects
    existing_projects = db.execute("SELECT * FROM projects")

    # modify title for tv series
    # and construct project name to be displayed
    for project in existing_projects:
        if project["type"] == "tv series":
            project["title"] = (project["title"] + " - s" + str(project["season"]) + \
                               "e" + str(project["episode"]))
        project["name"] = "[" + project["type"] + "] " + project["title"] + " - " + \
                          project["author"] + " (" + str(project["year"]) + ")"




    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure project submitted and ...
        if not request.form.get("project"):
            return apology("Must choose project to update.")
        else:
            project_name = request.form.get("project").lower()

        # ... ensure project exists
        project_id = -1
        for project in existing_projects:
            if project["name"].lower() == project_name:
                project_id = project["id"]
                break
        if project_id == -1:
            return apology("Must choose among existing projects (better select from the dropdown menu).")

        # get project metadata
        rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
        session["existing_project"] = rows[0]

        # ENSURE FILE SELECTED FOR UPLOAD
        # http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
        # check if the post request has the file part
        if 'file' not in request.files:
            session.pop('existing_project', None)
            return apology("Couldn't update this project.", "Please select a file to upload.")

        # if user does not select file, browser also
        # submit a empty part without filename
        file = request.files['file']
        if not file or file.filename == '':
            session.pop('existing_project', None)
            return apology("Couldn't update this project.", "Please select a file to upload.")

        # ensure file name (extension) allowed
        if forbidden_file(file.filename):
            session.pop('existing_project', None)
            return apology("Couldn't update this project.",
                           "Allowed extensions: xls/xlsx/xlsm/xltx/xltm.")

        # ensure 1 <-> 5 language versions
        workbook = openpyxl.load_workbook(file)
        session["existing_project"]["number_of_versions"] = len(workbook.worksheets)

        if session["existing_project"]["number_of_versions"] > 5:
            session.pop('existing_project', None)
            return apology("Couldn't update the project with your file.",
                           "Don't overwork - neither yourself, nor the server (maximum 5 language versions allowed per file).")
        elif session["existing_project"]["number_of_versions"] < 1:
            session.pop('existing_project', None)
            return apology("Couldn't update the project with your file.",
                           "You must contribute with at least one language version.")

        # make sure all the new versions have the same number of lines as the original project
        for worksheet in workbook:
            if worksheet.max_row != session["existing_project"]["line_count"]:
                line_count = session["existing_project"]["line_count"]
                session.pop('existing_project', None)
                return apology("Couldn't update the project with your file.",
                               "New versions have to have the same number of lines as the original project (%s)." % line_count)

        # save all the lines
        # https://stackoverflow.com/questions/13377793/is-it-possible-to-get-an-excel-documents-row-count-without-loading-the-entire-d
        session["existing_project"]["lines"] = []
        for worksheet in workbook:
            l = []
            for row in worksheet.iter_rows(min_row=1, max_col=1, max_row=session["existing_project"]["line_count"]):
                for cell in row:
                    value = str(cell.value)
                    l.append(value)
            session["existing_project"]["lines"].append(l)

        return render_template("existing_project_versions.html")

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:

        # return the list of projects for the user to choose from
        return render_template("upload_existing.html", existing_projects=existing_projects)

# add to existing project - project versions
@app.route("/existing_project_versions", methods=["GET", "POST"])
@login_required
def existing_project_versions():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # save language versions
        session["existing_project"]["versions"] = []
        for i in range(session["existing_project"]["number_of_versions"]):
            session["existing_project"]["versions"].append(request.form.get(str(i)).lower())

        # upload new language versions
        # prepare to delete, if something goes wrong
        timestamps = []
        for i in range(session["existing_project"]["number_of_versions"]):
            timestamp=strftime("%H:%M:%S %Y-%m-%d", gmtime())
            timestamps.append(timestamp)
            try:
                db.execute("INSERT INTO versions (project_id, user_id, language, timestamp) VALUES(:project_id, \
                           :user_id, :language, :timestamp)", project_id=session["existing_project"]["id"],
                           user_id=session["user_id"], language=session["existing_project"]["versions"][i],
                           timestamp=timestamp)
            except RuntimeError:
                for timestamp in timestamps:
                    db.execute("DELETE FROM 'versions' WHERE timestamp = :timestamp", timestamp=timestamp)
                session.pop('existing_project', None)
                return apology("Couldn't save the new language versions in the database.")

        # get the IDs of the new versions
        # https://stackoverflow.com/questions/10897339/python-fetch-first-10-results-from-a-list
        # https://stackoverflow.com/questions/3940128/how-can-i-reverse-a-list-in-python
        version_ids = []
        rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id ORDER BY id DESC",
                          project_id=session["existing_project"]["id"])
        for row in rows:
            version_ids.append(row["id"])
        version_ids = version_ids[:session["existing_project"]["number_of_versions"]]
        version_ids = list(reversed(version_ids))

        # upload the lines for each version
        # https://stackoverflow.com/questions/522563/accessing-the-index-in-python-for-loops
        for i in range(session["existing_project"]["number_of_versions"]):
            for index, line in enumerate(session["existing_project"]["lines"][i]):
                try:
                    db.execute("INSERT INTO lines (project_id, version_id, line_index, line) \
                               VALUES (:project_id, :version_id, :line_index, :line)",
                               project_id=session["existing_project"]["id"],
                               version_id=version_ids[i], line_index=index, line=line)
                except RuntimeError:
                    for id in version_ids:
                        db.execute("DELETE FROM 'lines' WHERE version_id = :version_id", version_id=id)
                    db.execute("DELETE FROM 'projects' WHERE id = :id", id=session["existing_project"]["id"])
                    db.execute("DELETE FROM 'versions' WHERE project_id = :project_id",
                               project_id=session["existing_project"]["id"])
                    session.pop('existing_project', None)
                    return apology("Couldn't save the new lines in the database.")

        # if successful, pop the session variable and inform
        # personalize the message just to be kewl
        if session["existing_project"]["type"].lower() == "tv series":
                session["existing_project"]["title"] += (" (s" + str(session["existing_project"]["season"]) + \
                                                        "/(e" + str(session["existing_project"]["episode"]) +")")
        s = "\"" + session["existing_project"]["title"].title() + "\"" + " by " + \
            session["existing_project"]["author"].title() + " has been successfully updated."
        session.pop('existing_project', None)
        return success(s)

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return upload_existing()


# route with parameters
# https://stackoverflow.com/questions/14032066/can-flask-have-optional-url-parameters
# display project info
@app.route("/view_project/<id>")
def view_project(id):

    # get project metadata
    rows = db.execute("SELECT * FROM projects WHERE id = :id", id=id)
    project = rows[0]

    # if tv series, make title include the season & episode
    if project["type"].lower() == "tv series":
        project["title"] += (" (s" + str(project["season"]) + "/e" + str(project["episode"]) +")")

    # get project languages
    rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id", project_id=id)
    language_list = []
    for row in rows:
        if row["language"] not in language_list:
            language_list.append(row["language"])

    languages = ""
    for language in language_list:
        languages += (language + ", ")
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

            # if tv series, make title include the season & episode
            if project["type"].lower() == "tv series":
                project["title"] += (" (s" + str(rows[0]["season"]) + "/e" + str(rows[0]["episode"]) +")")


    # get user's uploaded projects
    uploaded_projects = db.execute("SELECT * FROM projects WHERE user_id = :user_id",
                                   user_id=session["user_id"])

    # get only the user's versions for his projects
    if len(uploaded_projects) > 0:
        for project in uploaded_projects:

            # if tv series, make title include the season & episode
            if project["type"].lower() == "tv series":
                project["title"] += (" (s" + str(project["season"]) + "/e" + str(project["episode"]) +")")


            rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id AND user_id = :user_id",
                              project_id=project["id"], user_id=session["user_id"])

            languages_list = []
            for row in rows:
                if row["language"] not in languages_list:
                    languages_list.append(row["language"])
            languages_list = sorted(languages_list)

            languages_string = ""
            for language in languages_list:
                languages_string += (language + ", ")

            languages_string = languages_string[:-2]
            project["languages"] = languages_string


    # get user's uploaded versions for other users' projects
    user_projects = []
    for project in uploaded_projects:
        user_projects.append(project["id"])

    uploaded_versions = db.execute("SELECT * FROM versions WHERE user_id = :user_id",
                                   user_id=session["user_id"])

    user_versions = []
    for version in uploaded_versions:
        if version["project_id"] not in user_projects:
            if version["project_id"] not in user_versions:
                user_versions.append(version)

    not_user_project_ids = []
    for version in user_versions:
        if version["project_id"] not in not_user_project_ids:
            not_user_project_ids.append(version["project_id"])

    # get projects' metadata
    not_user_projects = []
    if len(not_user_project_ids) > 0:

        for id in not_user_project_ids:
            project = {}
            project["id"] = id
            rows = db.execute("SELECT * FROM projects WHERE id = :id", id=id)
            project["type"] = rows[0]["type"]
            project["title"] = rows[0]["title"]
            project["author"] = rows[0]["author"]
            project["year"] = rows[0]["year"]


            # if tv series, make title include the season & episode
            if project["type"].lower() == "tv series":
                project["title"] += (" (s" + str(rows[0]["season"]) + "/e" + str(rows[0]["episode"]) +")")

            # add user's language versions
            rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id AND user_id = :user_id",
                              project_id=id, user_id=session["user_id"])

            languages_list = []
            for row in rows:
                if row["language"] not in languages_list:
                    languages_list.append(row["language"])
            languages_list = sorted(languages_list)

            languages_string = ""
            for language in languages_list:
                languages_string += (language + ", ")

            languages_string = languages_string[:-2]
            project["languages"] = languages_string

            not_user_projects.append(project)

    # render the account history page, passing in the data
    return render_template("account_history.html", started_projects=started_projects,
                           uploaded_projects=uploaded_projects, not_user_projects=not_user_projects)


# prepare to delete
@app.route("/prepare_deletion", methods=["GET", "POST"])
@login_required
def prepare_deletion():

    if request.method == "POST":

        # get the id of the project to delete
        project_id = request.form.get('delete_project')

        # get the project metadata
        rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
        project = rows[0]

        # if tv series, make title include the season & episode
        if project["type"].lower() == "tv series":
            project["title"] += (" (s" + str(rows[0]["season"]) + "/e" + str(rows[0]["episode"]) +")")


        project["versions_to_delete"] = db.execute("SELECT * FROM versions WHERE project_id = :project_id AND \
                                                   user_id = :user_id ORDER BY language ASC", project_id=project_id,
                                                   user_id=session["user_id"])

        return render_template("delete.html", project=project)

    else:
        return view_history()


# delete uploaded project route
@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():

    # if route reached via POST
    # i.e. one of the delete buttons pressed
    if request.method == "POST":

        # if trying to delete the project entirely
        if request.form.get('delete_project'):

            # get the project id
            project_id = request.form.get('delete_project')

            # bit redundant, but you can only delete your own projects
            rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
            if rows[0]["user_id"] != session["user_id"]:
                return apology("Couldn't delete this project.", "You can only delete your own projects.")


            # if other users contributed to this project, the user can't delete the project itself
            rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id", project_id=project_id)
            for row in rows:
                if row["user_id"] != session["user_id"]:
                    return apology("Can't delete this project. Other users have contributed to it.",
                                   "Try deleting versions separately instead.")

            # can't delete the project if used by somebody else
            rows = db.execute("SELECT * FROM history WHERE project_id = :project_id", project_id=project_id)
            for row in rows:
                if row["user_id"] != session["user_id"]:
                    return apology("Can't delete this project. Somebody is using it for practice.",
                                   "Try deleting versions separately instead.")

            # project can be deleted, so
            # deleting any corrections first
            try:
                db.execute("DELETE FROM corrections WHERE project_id = :project_id", project_id=project_id)
            except RuntimeError:
                return apology("Couldn't delete this project.", "Please try again.")

            # then the lines
            try:
                db.execute("DELETE FROM lines WHERE project_id = :project_id", project_id=project_id)
            except RuntimeError:
                return apology("Couldn't delete this project.", "Please try again.")

            # then the versions
            try:
                db.execute("DELETE FROM versions WHERE project_id = :project_id", project_id=project_id)
            except RuntimeError:
                return apology("Couldn't delete this project.", "Please try again.")

            # remove the poster
            rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], rows[0]["poster"]))
            except RuntimeError:
                return apology("Couldn't delete this project.", "Please try again.")

            # then the project itself
            try:
                db.execute("DELETE FROM projects WHERE id = :id", id=project_id)
            except RuntimeError:
                return apology("Couldn't delete this project.", "Please try again.")

        # if deleting versions one by one
        elif request.form.get('delete_version'):

            # get the version id
            version_id = request.form.get('delete_version')

            # bit redundant, but you can only delete your own versions
            rows = db.execute("SELECT * FROM versions WHERE id = :id", id=version_id)
            if rows[0]["user_id"] != session["user_id"]:
                return apology("Can only delete your own versions.")

            # ''' make sure 2+ different language versions uploaded by the same user are left '''
            # get the project id
            project_id = rows[0]["project_id"]

            # get all the versions of this project
            other_versions = db.execute("SELECT * FROM versions WHERE project_id = :project_id AND NOT id = :id",
                                        project_id=project_id, id=version_id)

            # if only one version remains
            if len(other_versions) == 1:
                return apology("Couldn't proceed with the deletion.",
                               "At least two different language versions uploaded by the same user should remain \
                               (for practice/deletion purposes).")

            # if 2+ versions remain
            elif len(other_versions) >= 2:

                same_user_different_versions = False
                users_languages = {}

                for version in other_versions:
                    if version["user_id"] not in users_languages:
                        users_languages[version["user_id"]] = version["language"]
                    else:
                        if users_languages[version["user_id"]] != version["language"]:
                            same_user_different_versions = True
                            break

                if not same_user_different_versions:
                    return apology("Couldn't proceed with the deletion.",
                                   "None or at least two different language versions uploaded by the same user should remain.")
            # ''' made sure 2+ different language versions uploaded by the same user are left '''


            # version can be deleted, so
            # deleting any corrections first
            try:
                db.execute("DELETE FROM corrections WHERE version_id = :version_id", version_id=version_id)
            except RuntimeError:
                return apology("Couldn't proceed with the deletion.", "Please try again.")

            # then the lines
            try:
                db.execute("DELETE FROM lines WHERE version_id = :version_id", version_id=version_id)
            except RuntimeError:
                return apology("Couldn't proceed with the deletion.", "Please try again.")

            # then the version itself
            try:
                db.execute("DELETE FROM versions WHERE id = :id", id=version_id)
            except RuntimeError:
                return apology("Couldn't proceed with the deletion.", "Please try again.")

            # if no versions left for the project, delete the project itself
            remaining_versions = db.execute("SELECT * FROM versions WHERE project_id = :project_id \
                                            ORDER BY timestamp ASC", project_id=project_id)

            if len(remaining_versions) == 0:

                # remove the poster
                rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
                try:
                    os.remove(rows[0]["poster"])
                except RuntimeError:
                    return apology("Deleted the versions, but not the project.", "Please try again.")

                try:
                    db.execute("DELETE FROM projects WHERE id = :id", id=project_id)
                except RuntimeError:
                    return apology("Deleted the versions, but not the project.", "Please try again.")

            # if no versions of the original user remain
            # change the project user to the next one with the oldest two different versions
            different_user_needed = True
            for version in remaining_versions:
                if version["user_id"] == session["user_id"]:
                    different_user_needed = False
                    break

            if different_user_needed:

                users_languages = {}

                for version in remaining_versions:
                    if version["user_id"] not in users_languages:
                        users_languages[version["user_id"]] = version["language"]
                    else:
                        if users_languages[version["user_id"]] != version["language"]:
                            try:
                                db.execute("UPDATE projects SET user_id = :user_id WHERE id = :id",
                                           user_id=version["user_id"], id=project_id)
                            except RuntimeError:
                                return apology("Couldn't change the owner of the project.")
                            break


        # back to account history after deletion
        return view_history()

    # else if user reached route via GET (as by clicking a link or via redirect)
    # redirect to account history to choose project to delete
    else:
        return view_history()


# edit uploaded project route
@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():

    # if user reached route via POST (as by submitting a form via POST)
    # Different types of POST requests in the same route in Flask
    # https://stackoverflow.com/questions/43333440/different-types-of-post-requests-in-the-same-route-in-flask
    if request.method == "POST":

        # if user prepares to edit project from the account history page
        if request.form.get('want_to_edit_project'):

            project_id = request.form.get('want_to_edit_project')
            rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
            project = rows[0]

            # if tv series, make title include the season & episode
            if project["type"].lower() == "tv series":
                project["title"] += (" (s" + str(project["season"]) + "/e" + str(project["episode"]) +")")

            # get user project languages
            rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id AND user_id = :user_id",
                                  project_id=project_id, user_id=session["user_id"])

            language_list = []
            for row in rows:
                if row["language"] not in language_list:
                    language_list.append(row["language"])

            languages = ""
            for language in language_list:
                languages += (language + ", ")
            languages = languages[:-2]
            project["languages"] = languages

            return render_template("edit.html", project=project)

        # else if user chooses what he wants to change specifically
        else:

            # if user wants to change type
            if request.form.get('want_to_edit_type'):

                project_id = request.form.get('want_to_edit_type')
                rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
                project = rows[0]

                return render_template("edit_type.html", project=project)

            # if user wants to change name
            if request.form.get('want_to_edit_name'):

                project_id = request.form.get('want_to_edit_name')
                rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
                project = rows[0]

                return render_template("edit_name.html", project=project)

            # if user wants to change poster
            if request.form.get('want_to_edit_poster'):

                project_id = request.form.get('want_to_edit_poster')
                rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
                project = rows[0]

                return render_template("edit_poster.html", project=project)

            # if user wants to change description
            if request.form.get('want_to_edit_description'):

                project_id = request.form.get('want_to_edit_description')
                rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
                project = rows[0]

                return render_template("edit_description.html", project=project)

            # if user wants to change one of his project versions
            if request.form.get('want_to_edit_versions'):

                project_id = request.form.get('want_to_edit_description')
                rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
                project = rows[0]

                # get user project versions
                rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id AND user_id = :user_id",
                                  project_id=project_id, user_id=session["user_id"])
                versions = []
                for row in rows:
                    versions.append(row["language"])
                project["versions"] = versions

                return render_template("edit_versions.html", project=project)


            # if user actually changes type
            if request.form.get('change_project_type'):

                # get the project id and the new type
                project_id = request.form.get('change_project_type')
                rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
                project = rows[0]
                new_type = request.form.get('new_type').lower()

                # new type must differ
                if project["type"] == new_type:
                    return apology("Couldn't edit project.", "Make sure the new type differs from the current one.")

                # if new type tv series, render the input season/episode template
                if new_type == "tv series":
                    return render_template("edit_episode.html", project=project)

                # otherwise, make sure project wouldn't exist already in its new form
                rows = db.execute("SELECT * FROM projects WHERE type = :type AND title = :title AND author = :author AND \
                                  year = :year", type=new_type, title=project["title"], author=project["author"], year=project["year"])
                if len(rows) > 0:
                    return apology("This project already exists.")

                # try to edit
                try:
                    db.execute("UPDATE projects SET type = :type, season = NULL, episode = NULL WHERE id = :id", type=new_type, id=project_id)
                except RuntimeError:
                    return apology("Couldn't update the project.", "Please try again later.")

                return view_history()

            # if user actually changes type to tv series
            if request.form.get('change_to_tv_series'):

                # make sure episode submitted
                if not request.form.get('new_episode') or not request.form.get('new_season'):
                    return apology("Couldn't edit project.", "Please input the season and/or episode.")

                # get the project id and the episode/season
                project_id = request.form.get('change_to_tv_series')
                rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
                project = rows[0]
                new_episode = request.form.get('new_episode')
                new_season = request.form.get('new_season')

                # make sure project wouldn't exist already in its new form
                rows = db.execute("SELECT * FROM projects WHERE type = 'tv series' AND title = :title AND author = :author AND \
                                  year = :year AND season = :season AND episode = :episode", title=project["title"],
                                  author=project["author"], year=project["year"], season=new_season, episode=new_episode)
                if len(rows) > 0:
                    return apology("This project already exists.")

                # try to edit
                try:
                    db.execute("UPDATE projects SET type = 'tv series', season = :season, episode = :episode WHERE id = :id",
                               season=new_season, episode=new_episode, id=project_id)
                except RuntimeError:
                    return apology("Couldn't update the project.", "Please try again later.")

                return view_history()

            # if user actually changes name
            if request.form.get('change_project_name'):

                # get the project id and the episode/season
                project_id = request.form.get('change_project_name')
                rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
                project = rows[0]

                # ensure something is being changed
                if not request.form.get('change_title') and not request.form.get('change_author') and \
                not request.form.get('change_year'):
                    if project["type"] == "tv series":
                        if not request.form.get('change_season') and not request.form.get('change_episode'):
                            return apology("Gotta change something.")
                    else:
                        return apology("Gotta change something.")

                # make sure project to-be-changed isn't changed into an existing project
                if request.form["change_title"]:
                    title = request.form["change_title"].lower()
                else:
                    title = project["title"].lower()

                if request.form["change_author"]:
                    author = request.form["change_author"].lower()
                else:
                    author = project["author"].lower()

                if request.form["change_year"]:
                    year = request.form["change_year"]
                else:
                    year = project["year"]

                if project["type"] == "tv series":
                    if request.form["change_season"]:
                        season = request.form["change_season"]
                    else:
                        season = project["season"]

                    if request.form["change_episode"]:
                        episode = request.form["change_episode"]
                    else:
                        episode = project["episode"]

                if project["type"] == "tv series":
                    rows = db.execute("SELECT * FROM projects WHERE type = :type AND title = :title AND \
                                      author = :author AND year = :year AND season = :season AND episode = :episode",
                                      type=project["type"], title=title, author=author, year=year, season=season, episode=episode)
                else:
                    rows = db.execute("SELECT * FROM projects WHERE type = :type AND title = :title AND author = :author AND \
                                      year = :year", type=project["type"], title=title, author=author, year=year)

                if len(rows) > 0:
                    return apology("This project already exists.")

                # try to edit the metadata
                try:
                    if request.form["change_title"]:
                        db.execute("UPDATE projects SET title = :title WHERE id = :id",
                                   title=request.form["change_title"].lower(), id=project_id)

                    if request.form["change_author"]:
                        db.execute("UPDATE projects SET author = :author WHERE id = :id",
                                   author=request.form["change_author"].lower(), id=project_id)

                    if request.form["change_year"]:
                        db.execute("UPDATE projects SET year = :year WHERE id = :id",
                                   year=request.form["change_year"], id=project_id)

                    if project["type"] == "tv series":
                        if request.form["change_season"]:
                            db.execute("UPDATE projects SET season = :season WHERE id = :id",
                                       season=request.form["change_season"], id=project_id)

                        if request.form["change_episode"]:
                            db.execute("UPDATE projects SET episode = :season WHERE id = :id",
                                       season=request.form["change_episode"], id=project_id)

                except RuntimeError:
                    return apology("Couldn't update the project.", "Please try again later.")

                return view_history()

            # if user actually changes poster
            if request.form.get('change_project_poster'):

                # get the project id, fetch the metadata
                project_id = request.form.get('change_project_poster')
                rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
                project = rows[0]

                # ENSURE NEW POSTER SELECTED FOR UPLOAD
                # http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
                # check if the post request has the file part
                if 'new_poster' not in request.files:
                    return apology("Couldn't edit this project.", "Please select a new poster image.")

                # if user does not select file, browser also
                # submit a empty part without filename
                file = request.files['new_poster']
                if not file or file.filename == '':
                    return apology("Couldn't edit this project.", "Please select a new poster image.")

                # ensure poster file (extension) allowed
                if forbidden_poster(file.filename):
                    return apology("Couldn't edit this project.",
                                   "Allowed extensions for poster images: jpeg/jpeg/png/svg.")

                # ensure poster image not too large
                # https://stackoverflow.com/questions/2104080/how-to-check-file-size-in-python
                old_file_position = file.tell()
                file.seek(0, os.SEEK_END)
                size = file.tell()
                file.seek(old_file_position, os.SEEK_SET)
                print(size)
                if size > 307200:
                    return apology("Couldn't edit this project.", "Maximum size for poster images is 300 KB.")

                # try to upload the new poster
                try:
                    postername = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], postername))
                except RuntimeError:
                    return apology("Couldn't edit this project.", "Please try again later.")

                # try to remove the old poster
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], project["poster"]))
                except RuntimeError:
                    return apology("Couldn't edit this project.", "Please try again.")

                # try to edit the metadata
                try:
                    db.execute("UPDATE projects SET poster = :poster WHERE id = :id", poster=postername, id=project_id)
                except RuntimeError:
                    return apology("Couldn't update the project.", "Please try again later.")

                return view_history()

            # if user actually changes description
            if request.form.get('change_project_description'):

                # get the project id and the new type
                project_id = request.form.get('change_project_description')
                rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
                project = rows[0]

                # ensure description of the project was submitted, save it
                if not request.form.get("new_description"):
                    return apology("Couldn't update this project.", "Please provide a new description.")
                else:
                    new_description = request.form.get('new_description')

                # make sure description not too long
                if len(new_description) > 1000:
                    return apology("Didn't edit the project.", "New Description too long (maximum 1000 characters).")

                # try to edit
                try:
                    db.execute("UPDATE projects SET description = :description WHERE id = :id",
                               description=new_description, id=project_id)
                except RuntimeError:
                    return apology("Couldn't update the project.", "Please try again later.")

                return view_history()

            # if user actually changes language version
            if request.form.get('change_project_versions'):

                # get the project id and the new version language
                project_id = request.form.get('change_project_versions')
                rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
                project = rows[0]
                from_version_id = request.form.get('change_from_version')
                to_version = request.form.get('change_to_version').lower()

                # new version language must differ
                rows = db.execute("SELECT * FROM versions WHERE id = :id", id=from_version_id)
                if rows[0]["language"] == to_version:
                    return apology("Didn't update the project.", "New version language must differ from the old one.")

                # make sure we would be left with at least two different language versions for this project
                rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id AND NOT id = :id",
                                  project_id=project_id, id=from_version_id)
                remaining_languages = []
                for row in rows:
                    remaining_languages.append(row["language"])
                remaining_languages.append(to_version)
                if len(set(remaining_languages)) < 2:
                    return apology("Couldn't update the project.",
                                   "Must have at least two different language versions for every project.")

                # try to edit
                try:
                    db.execute("UPDATE versions SET language = :language WHERE id = :id", language=to_version, id=from_version_id)
                except RuntimeError:
                    return apology("Couldn't update the project.", "Please try again later.")

                return view_history()

    # else if user reached route via GET (as by clicking a link or via redirect)
    # redirect to account history to choose project to edit
    else:
        return view_history()


# prepare project for practice route
@app.route("/prepare_practice", methods=["GET", "POST"])
def prepare_practice():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        project_id = request.form["prepare_practice"]
        rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
        project = rows[0]
        project["versions"] = db.execute("SELECT * FROM versions WHERE project_id = :project_id", project_id=project_id)

        return render_template("prepare_practice.html", project=project)

    # else if user reached route via GET (as by clicking a link or via redirect)
    # redirect to project browsing page
    else:
        return browse()


# practice route
@app.route("/project_practice", methods=["GET", "POST"])
def project_practice():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # get project metadata
        project_id = request.form.get("start_practice")
        rows = db.execute("SELECT * FROM projects WHERE id = :id", id=project_id)
        project = rows[0]

        # ensure translate from & to languages submitted
        if not request.form.get("from_version_id") or not request.form.get("to_version_id"):
            return apology("Couldn't start practice.", "Please choose from & to which language to translate.")
        else:
            from_version_id = request.form.get("from_version_id")
            to_version_id = request.form.get("to_version_id")

        # make sure from & to languages different
        rows = db.execute("SELECT * FROM versions WHERE id = :id", id=from_version_id)
        project["from_version"] = rows[0]
        rows = db.execute("SELECT * FROM versions WHERE id = :id", id=to_version_id)
        project["to_version"] = rows[0]
        if from_version_id == to_version_id or project["from_version"]["language"] == project["to_version"]["language"]:
            return apology("Couldn't start practice.", "From & to languages must differ.")

        # prepare the starting point
        # if user logged in, check whether project already started
        # https://stackoverflow.com/questions/3845362/python-how-can-i-check-if-the-key-of-an-dictionary-exists
        starting_line = 0
        if "user_id" in session:
            rows = db.execute("SELECT * FROM history WHERE user_id = :user_id AND from_version_id = :from_version_id AND \
                               to_version_id = :to_version_id", user_id=session["user_id"], from_version_id=from_version_id,
                               to_version_id=to_version_id)
            if len(rows) > 0:
                starting_line = rows[0]["progress"]


        # prepare lines and project for rendering
        from_lines = []
        rows = db.execute("SELECT * FROM lines WHERE version_id = :version_id ORDER BY id ASC", version_id=from_version_id)
        for row in rows:
            from_lines.append(row["line"])

        # prepare lines and project for rendering
        to_lines = []
        rows = db.execute("SELECT * FROM lines WHERE version_id = :version_id ORDER BY id ASC", version_id=to_version_id)
        for row in rows:
            to_lines.append(row["line"])

        return render_template("project_practice.html", starting_line=starting_line, from_lines=from_lines, to_lines=to_lines,
                                                        project=project)

    # else if user reached route via GET (as by clicking a link or via redirect)
    # redirect to project browsing page
    else:
        return browse()

# the about route (the purpose of this website)
@app.route("/about")
def about():
    return render_template("about.html")


# contact info route
@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/browse")
def browse():

    projects = db.execute("SELECT * FROM projects")

    # if tv series, make title include the season & episode
    for project in projects:
        if project["type"].lower() == "tv series":
            project["title"] += (" (s" + str(project["season"]) + "/e" + str(project["episode"]) +")")

    return render_template("browse.html", projects=projects)


# edit version line
@app.route("/edit_line", methods=["GET", "POST"])
@login_required
def edit_line():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # if user prepares to edit line from practice page
        if request.form.get('line_to_edit'):

            # get the line index, and the versions ids
            line_to_edit = request.form.get("line_to_edit").split(",")
            line_index = line_to_edit[0]
            bad_version_id = line_to_edit[1]
            good_version_id = line_to_edit[2]

            # get the line id and the lines themselves
            rows = db.execute("SELECT * FROM lines WHERE version_id = :version_id AND line_index = :line_index",
                              version_id=good_version_id, line_index=line_index)
            good_line = rows[0]["line"]
            rows = db.execute("SELECT * FROM lines WHERE version_id = :version_id AND line_index = :line_index",
                              version_id=bad_version_id, line_index=line_index)
            bad_line = rows[0]["line"]
            bad_line_id = rows[0]["id"]

            # render the template with the corresponding variables
            return render_template("edit_line.html", good_line=good_line, bad_line=bad_line, bad_line_id=bad_line_id)

        # else if user actually changes a specific line from the edit line template
        elif request.form.get('edit_line'):

            # make sure new line text provided, save it
            if not request.form.get("edit_line_text"):
                return apology("Couldn't edit anything.", "Please make sure you input the new line.")
            else:
                line_text = request.form.get("edit_line_text")

            # get the line id
            line_id = request.form.get("edit_line")

            # try to edit the line
            try:
                db.execute("UPDATE lines SET line = :line WHERE id = :id", line=line_text, id=line_id)
            except RuntimeError:
                    return apology("Couldn't edit this line.", "Please try again later.")

            return success("The line has been successfully updated.")

    # else if user reached route via GET (as by clicking a link or via redirect)
    # redirect to project browsing page
    else:
        return browse()


# correct version line
@app.route("/correct_line", methods=["GET", "POST"])
@login_required
def correct_line():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # if user prepares to correct line from practice page
        if request.form.get('line_to_correct'):

            # get the line index, and the versions ids
            line_to_correct = request.form.get("line_to_correct").split(",")
            line_index = line_to_correct[0]
            bad_version_id = line_to_correct[1]
            good_version_id = line_to_correct[2]

            # get the line id and the lines themselves
            rows = db.execute("SELECT * FROM lines WHERE version_id = :version_id AND line_index = :line_index",
                              version_id=good_version_id, line_index=line_index)
            good_line = rows[0]["line"]
            good_line_id = rows[0]["id"]
            rows = db.execute("SELECT * FROM lines WHERE version_id = :version_id AND line_index = :line_index",
                              version_id=bad_version_id, line_index=line_index)
            bad_line = rows[0]["line"]
            bad_line_id = rows[0]["id"]

            # render the template with the corresponding variables
            return render_template("correct_line.html", good_line=good_line, good_line_id=good_line_id,
                                                        bad_line=bad_line, bad_line_id=bad_line_id)

        # else if user actually changes a specific line from the edit line template
        elif request.form.get('correct_line'):

            # make sure new line text provided, save it
            if not request.form.get("correct_line_text"):
                return apology("Couldn't correct anything.", "Please make sure you input the new corrected text.")
            else:
                line_text = request.form.get("correct_line_text")

            # get the good line id, bad line id and its metadata
            line_to_correct = request.form.get("correct_line").split(",")
            context_line_id = line_to_correct[0]
            line_id = line_to_correct[1]
            rows = db.execute("SELECT * FROM lines WHERE id = :id", id=line_id)
            line = rows[0]

            # save the correction
            try:
                db.execute("INSERT INTO corrections (line_id, correction, user_id, project_id, version_id, context_line_id) \
                           VALUES (:line_id, :correction, :user_id, :project_id, :version_id, :context_line_id)",
                           line_id=line["id"], correction=line_text, user_id=session["user_id"], project_id=line["project_id"],
                           version_id=line["version_id"], context_line_id=context_line_id)
            except RuntimeError:
                    return apology("Couldn't correct this line.", "Please try again later.")

            return success("The correction has been submitted to the owner of the project.")

    # else if user reached route via GET (as by clicking a link or via redirect)
    # redirect to project browsing page
    else:
        return browse()


# view notifications route
@app.route("/view_notifications")
@login_required
def view_notifications():

    # fetch user's versions
    versions = db.execute("SELECT * FROM versions WHERE user_id = :user_id", user_id=session["user_id"])

    # fetch the proposed line corrections for these versions
    corrections = []
    for version in versions:
        rows = db.execute("SELECT * FROM corrections WHERE version_id = :version_id", version_id=version["id"])
        for row in rows:
            corrections.append(row)

    # gather the metadata
    notifications = []
    for correction in corrections:
        notification = {}
        rows = db.execute("SELECT * FROM projects WHERE id = :project_id", project_id=correction["project_id"])
        notification["title"] = rows[0]["title"]
        rows = db.execute("SELECT * FROM lines WHERE id = :id", id=correction["context_line_id"])
        notification["context_line"] = rows[0]["line"]
        from_version_id = rows[0]["version_id"]
        rows = db.execute("SELECT * FROM versions WHERE id = :id", id=from_version_id)
        notification["from_language"] = rows[0]["language"]
        rows = db.execute("SELECT * FROM users WHERE id = :id", id=correction["user_id"])
        notification["user"] = rows[0]["username"]
        notification["suggested_line"] = correction["correction"]
        rows = db.execute("SELECT * FROM lines WHERE id = :id", id=correction["line_id"])
        notification["original_line"] = rows[0]["line"]
        to_version_id = rows[0]["version_id"]
        rows = db.execute("SELECT * FROM versions WHERE id = :id", id=to_version_id)
        notification["to_language"] = rows[0]["language"]
        notification["original_line_id"] = correction["line_id"]
        notification["correction_id"] = correction["id"]
        notifications.append(notification)

    return render_template("account_notifications.html", notifications=notifications)


# act upon suggested corrections
@app.route("/action_correction", methods=["GET", "POST"])
@login_required
def action_correction():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # if user accepts the suggested correction
        if request.form.get('implement_correction'):

            correction_id = request.form.get('implement_correction')
            rows = db.execute("SELECT * FROM corrections WHERE id = :id", id=correction_id)
            correction = rows[0]["correction"]
            corrected_line_id = rows[0]["line_id"]

            # change the line
            try:
                db.execute("UPDATE lines SET line = :line WHERE id = :id", line=correction, id=corrected_line_id)
            except RuntimeError:
                return apology("Couldn't implement the correction.", "Please try again later.")

            # delete the suggestion
            try:
                db.execute("DELETE FROM corrections WHERE id = :id", id=correction_id)
            except RuntimeError:
                return apology("Implemented the correction, couldn't delete it though.", "Please try again later.")

        # else if user directly discards the suggested correction
        if request.form.get('discard_correction'):

            # delete the suggestion
            try:
                db.execute("DELETE FROM corrections WHERE id = :id", id=request.form.get('discard_correction'))
            except RuntimeError:
                return apology("Couldn't delete the correction.", "Please try again later.")

        return view_notifications()

    # else if user reached route via GET (as by clicking a link or via redirect)
    # redirect to project browsing page
    else:
        return browse()



######################
# DONE UP UNTIL HERE #
######################















@app.route("/faq")
def faq():
    return


# prototype
@app.route("/whatever", methods=["GET", "POST"])
@login_required
def whatever():
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        pass

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("upload_new.html")
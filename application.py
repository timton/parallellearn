from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from time import gmtime, strftime
from random import shuffle

# for file uploading
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
UPLOAD_FOLDER = 'projects/'
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


@app.route("/upload_existing", methods=["GET", "POST"])
@login_required
def upload_existing():

    # query for all the existing projects
    existing_projects = db.execute("SELECT * FROM projects")

    # modify title for tv series
    for project in existing_projects:
        if project["type"] == "tv series":
            project["title"] = (project["title"] + " - s" + str(project["season"]) + \
                               "e" + str(project["episode"]))

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
            name = "[" + project["type"] + "] " + project["title"] + " - " + project["author"] + " (" + str(project["year"]) + ")"
            if name == project_name:
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

        # ensure 1 <-> 10 language versions
        workbook = openpyxl.load_workbook(file)
        session["existing_project"]["number_of_versions"] = len(workbook.worksheets)

        if session["existing_project"]["number_of_versions"] > 10:
            session.pop('existing_project', None)
            return apology("Couldn't update the project with your file.",
                           "Let's not overload the server (10 maximum language versions allowed per file).")
        elif session["existing_project"]["number_of_versions"] < 1:
            session.pop('existing_project', None)
            return apology("Couldn't update the project with your file.",
                           "You must contribute with at least one language version.")

        # make sure all the new versions have the same number of lines as the original project
        for worksheet in workbook:
            if worksheet.max_row != session["existing_project"]["line_count"]:
                session.pop('existing_project', None)
                return apology("Couldn't update the project with your file.",
                               "The new versions have to have the same number of lines as the original project.")

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
        # make the lines 1-indexed
        for i in range(session["existing_project"]["number_of_versions"]):
            for index, line in enumerate(session["existing_project"]["lines"][i]):
                try:
                    db.execute("INSERT INTO lines (project_id, version_id, line_index, line) \
                               VALUES (:project_id, :version_id, :line_index, :line)",
                               project_id=session["existing_project"]["id"],
                               version_id=version_ids[i], line_index=(index + 1), line=line)
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
@app.route("/view_project/<title>")
def view_project(title):

    # get project metadata
    rows = db.execute("SELECT * FROM projects WHERE title = :title", title=title)
    project = rows[0]

    # get project languages
    rows = db.execute("SELECT * FROM versions WHERE project_id = :id", id=project["id"])
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
            project["season"] = rows[0]["season"]
            project["episode"] = rows[0]["episode"]


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
            project["season"] = rows[0]["season"]
            project["episode"] = rows[0]["episode"]


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

        # make sure none or 2+ different language versions left for project if deleting current file
        # if one version would be left, delete it only if uploaded by the current user
        # How do I count unique values inside an array in Python?
        # https://stackoverflow.com/questions/12282232/how-do-i-count-unique-values-inside-an-array-in-python
        rows = db.execute("SELECT project_id FROM versions WHERE filepath = :filepath",
                          filepath=file_to_delete)
        project = rows[0]
        rows = db.execute("SELECT * FROM versions WHERE project_id = :project_id",
                          project_id=project["project_id"])
        languages_left = []
        for version in rows:
            if version["filepath"] != file_to_delete:
                languages_left.append(version["language"])
                if len(set(languages_left)) >= 2:
                    break

        if len(set(languages_left)) == 1:

            # make sure all remaining versions are uploaded by the same user
            same_user = True
            for version in rows:
                if version["user_id"] != session["user_id"]:
                    same_user = False
                    break

            if same_user:

                for version in rows:

                    # delete each version
                    try:
                        db.execute("DELETE FROM 'versions' WHERE id = :id", id=version["id"])
                    except RuntimeError:
                        return apology("couldn't delete all the remaining versions of this project")

                    # delete each file (only once, of course)
                    if os.path.isfile(version["filepath"]):
                        try:
                            os.remove(version["filepath"])
                        except RuntimeError:
                            return apology("couldn't delete this project")

                # delete the project as well
                try:
                    db.execute("DELETE FROM 'projects' WHERE id = :id", id=project['project_id'])
                except RuntimeError:
                    return apology("couldn't delete this project")

                # back to account history after deletion
                return view_history()
            else:
                return apology("can't delete project if only one language version remains")

        # save the project metadata (for project deletion purposes afterwards)
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

    # else if user reached route via GET (as by clicking a link or via redirect)
    # redirect to account history to choose project to delete
    else:
        return view_history()


# edit uploaded project route
@app.route("/edit_project", methods=["GET", "POST"])
@login_required
def edit_project():

    # if user reached route via POST (as by submitting a form via POST)
    # Different types of POST requests in the same route in Flask
    # https://stackoverflow.com/questions/43333440/different-types-of-post-requests-in-the-same-route-in-flask
    if request.method == "POST":

        # if user prepares to edit project from the account history page
        if len(request.form['edit_project']) > 0:

            file_to_edit = request.form['edit_project']
            versions = db.execute("SELECT * FROM versions WHERE filepath = :filepath ORDER BY sheet_number ASC",
                                  filepath=file_to_edit)
            version = versions[0]
            projects = db.execute("SELECT * FROM projects WHERE id = :id", id=version["project_id"])
            project = projects[0]

            # saving the values in session variables for outside use
            session["versions"] = versions
            session["project"] = project

            return render_template("edit_project.html", project=project, versions=versions)

        # if user is actually trying to edit the project from the edit project page
        else:

            # ensure something is being changed
            # flag variable
            nothing_changed = True

            # metadata needs to change only if original project uploaded by user
            if session["project"]["user_id"] == session["user_id"]:
                if request.form["change_title"] or request.form["change_author"] or \
                   request.form["change_year"] or request.form["change_type"]:
                       nothing_changed = False

                if nothing_changed:
                    if session["project"]["type"] == "tv series":
                        if request.form["change_season"] or request.form["change_episode"]:
                            nothing_changed = False

            # for non-original projects, at least a language has to change
            if nothing_changed:
                for version in session["versions"]:
                    language_version = "change_language" + str(version["sheet_number"])
                    original_language = version["language"]
                    changed_language = ""
                    if request.form[language_version]:
                        changed_language = request.form[language_version].lower()
                        if changed_language != original_language:
                            nothing_changed = False
                            break

            if nothing_changed:
                return apology("must change something")

            # again, some metadata check that only applies of for original projects
            if session["project"]["user_id"] == session["user_id"]:
                if session["project"]["type"] == "tv series":
                    if request.form["change_type"]:
                        if request.form["change_type"].lower() != "tv series":
                            if request.form["change_season"] or request.form["change_episode"]:
                                return apology("seasons/episodes apply for tv series only")
                else:
                    if request.form["change_type"]:
                        if request.form["change_type"].lower() == "tv series":
                            if not request.form["add_season"] or not request.form["add_episode"]:
                                return apology("must provide season and episode for tv series")
                        else:
                            if request.form["add_season"] or request.form["add_episode"]:
                                return apology("can provide season/episode only for tv series")

            # make sure project to-be-changed isn't changed into an existing project
            # again, it only applies of for original projects
            if session["project"]["user_id"] == session["user_id"]:
                if request.form["change_title"]:
                    title = request.form["change_title"].lower()
                else:
                    title = session["project"]["title"].lower()

                if request.form["change_author"]:
                    author = request.form["change_author"].lower()
                else:
                    author = session["project"]["author"].lower()

                if request.form["change_year"]:
                    year = request.form["change_year"]
                else:
                    year = session["project"]["year"]

                if request.form["change_type"]:
                    type = request.form["change_type"].lower()

                    if type == "tv series":
                        season = request.form["add_season"]
                        episode = request.form["add_episode"]
                    else:
                        if session["project"]["type"].lower() == "tv series":
                            season = session["project"]["season"]
                            episode = session["project"]["episode"]
                else:
                    type = session["project"]["type"].lower()

                    if type == "tv series":
                        if request.form["change_season"] and request.form["change_episode"]:
                            season = request.form["change_season"]
                            episode = request.form["change_episode"]
                        else:
                            season = session["project"]["season"]
                            episode = session["project"]["episode"]

                # make sure project in its changed version doesn't exist already
                if type == "tv series":
                    rows = db.execute("SELECT * FROM projects WHERE type = :type AND title = :title AND \
                                      author = :author AND year = :year AND season = :season AND episode = :episode",
                                      type=type, title=title, author=author, year=year, season=season, episode=episode)
                else:
                    rows = db.execute("SELECT * FROM projects WHERE type = :type AND title = :title AND author = :author AND \
                                      year = :year", type=type, title=title, author=author, year=year)

                if len(rows) > 0 and rows[0]["id"] != session["project"]["id"]:
                    return apology("this project already exists; try to update existing instead.")

            # after we made sure something is being changed and the changed project doesn't already exist
            # change metadata only if original project created by user
            if session["project"]["user_id"] == session["user_id"]:

                # change title
                if request.form["change_title"]:
                    try:
                        db.execute("UPDATE projects SET title = :title WHERE id = :id",
                                   title=request.form["change_title"].lower(), id=session["project"]["id"])
                    except RuntimeError:
                        return apology("error while changing project title")

                # change author
                if request.form["change_author"]:
                    try:
                        db.execute("UPDATE projects SET author = :author WHERE id = :id",
                                   author=request.form["change_author"].lower(), id=session["project"]["id"])
                    except RuntimeError:
                        return apology("error while changing project author")

                # change year
                if request.form["change_year"]:
                    try:
                        db.execute("UPDATE projects SET year = :year WHERE id = :id",
                                   year=request.form["change_year"], id=session["project"]["id"])
                    except RuntimeError:
                        return apology("error while changing project year")

                # change type and season/episode
                if request.form["change_type"]:

                    # ensure supported type submitted
                    if request.form["change_type"].lower() not in SUPPORTED_TYPES:
                        return apology("must provide correct type: book, movie, tv series, or song")


                    if request.form["change_type"].lower() != "tv series":
                        if session["project"]["type"].lower() == "tv series":
                            try:
                                db.execute("UPDATE projects SET type = :type, season = '', episode = '' \
                                           WHERE id = :id", type=request.form["change_type"].lower(),
                                           id=session["project"]["id"])
                            except RuntimeError:
                                return apology("error while changing project type")
                        else:
                            try:
                                db.execute("UPDATE projects SET type = :type WHERE id = :id",
                                           type=request.form["change_type"].lower(),
                                           id=session["project"]["id"])
                            except RuntimeError:
                                return apology("error while changing project type")
                    else:
                        try:
                            db.execute("UPDATE projects SET type = :type, season = :season, episode = :episode \
                                        WHERE id = :id", type=request.form["change_type"].lower(),
                                        season=request.form["add_season"], episode=request.form["add_episode"],
                                        id=session["project"]["id"])
                        except RuntimeError:
                            return apology("error while changing project type")

            # change language versions
            for version in session["versions"]:
                language_version = "change_language" + str(version["sheet_number"])
                if request.form[language_version]:

                    # make sure language supported
                    if request.form[language_version].lower() not in SUPPORTED_LANGUAGES:
                        return apology("must submit project in supported languages (better select)")

                    try:
                        db.execute("UPDATE versions SET language = :language WHERE id = :id",
                                   language=request.form[language_version].lower(), id=version["id"])
                    except RuntimeError:
                        return apology("error while changing language(s)")


            # prepare to rename file (recreate name)
            projects = db.execute("SELECT * FROM projects WHERE id = :id", id=session["project"]["id"])
            project = projects[0]
            versions = db.execute("SELECT * FROM versions WHERE filepath = :filepath ORDER BY sheet_number ASC",
                                  filepath=session["versions"][0]["filepath"])

            if project["type"] == "tv series":
                project["title"] += (" [s" + str(project["season"]) + "e" + str(project["episode"]) + "]")

            project_languages = " ("
            for version in versions:
                project_languages += (version["language"] + ", ")
            project_languages = project_languages[:-2]
            project_languages += ")"
            filename = "[" + project["type"] + "] " + project["title"] + " - " + project["author"] + " - " + \
                       str(project["year"]) + project_languages + "." + \
                       session["versions"][0]["filepath"].rsplit('.', 1)[1].lower()
            old_name = session["versions"][0]["filepath"]
            new_name = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # rename the file
            try:
                os.rename(old_name, new_name)
            except OSError:
                return apology("couldn't rename the changed project")

            # update the filepath for all the language versions
            for version in session["versions"]:
                try:
                    db.execute("UPDATE versions SET filepath = :filepath WHERE id = :id",
                               filepath=new_name, id=version["id"])
                except RuntimeError:
                    return apology("error while changing language(s)")

            # release session variables
            session.pop('project', None)
            session.pop('versions', None)

            # return to account history
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
        session["project"] = rows[0]
        session["versions"] = db.execute("SELECT * FROM versions WHERE project_id = :project_id",
                                         project_id=project_id)

        return render_template("prepare_practice.html", project=session["project"], versions=session["versions"])

    # else if user reached route via GET (as by clicking a link or via redirect)
    # redirect to project browsing page
    else:
        return browse()


# practice route
@app.route("/practice", methods=["GET", "POST"])
def practice():

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure translate from & to languages submitted
        if not request.form.get("from_version_id") or not request.form.get("to_version_id"):
            return apology("must choose from & to which language to translate")
        else:
            from_version_id = int(request.form.get("from_version_id"))
            to_version_id = int(request.form.get("to_version_id"))

        # ensure version supported by project
        project_versions = []
        for version in session["versions"]:
            project_versions.append(version["id"])

        if from_version_id not in project_versions or to_version_id not in project_versions:
            return apology("can only practice in project supported languages (better select)")

        # make sure from & to languages different
        if from_version_id == to_version_id:
            return apology("from & to languages must differ")

        project=session["project"]

        # prepare versions and project for rendering
        rows = db.execute("SELECT * FROM versions WHERE id = :id", id=from_version_id)
        from_version = rows[0]
        project["from_language"] = from_version["language"]
        workbook = openpyxl.load_workbook(from_version["filepath"])
        from_worksheet = workbook.worksheets[(from_version["sheet_number"] - 1)]

        from_lines = []
        for row in from_worksheet.iter_rows(min_row=1, max_col=1, max_row=project["line_count"]):
            for cell in row:
                value = str(cell.value)
                from_lines.append(value)

        rows = db.execute("SELECT * FROM versions WHERE id = :id", id=to_version_id)
        to_version = rows[0]
        project["to_language"] = to_version["language"]
        workbook = openpyxl.load_workbook(to_version["filepath"])
        to_worksheet = workbook.worksheets[(to_version["sheet_number"] - 1)]

        to_lines = []
        for row in to_worksheet.iter_rows(min_row=1, max_col=1, max_row=project["line_count"]):
            for cell in row:
                value = str(cell.value)
                to_lines.append(value)

        # release session variables
        session.pop('project', None)
        session.pop('versions', None)

        return render_template("project_practice.html", from_lines=from_lines, to_lines=to_lines, project=project)

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



######################
# DONE UP UNTIL HERE #
######################
















@app.route("/browse")
def browse():
    return

@app.route("/faq")
def faq():
    return





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
            session["new_project"]["author"] = request.form.get("new_project_author")

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

        # ensure 2 <-> 10 language versions
        workbook = openpyxl.load_workbook(file)
        session["new_project"]["number_of_versions"] = len(workbook.worksheets)

        if session["new_project"]["number_of_versions"] > 10:
            session.pop('new_project', None)
            return apology("Couldn't upload this project.",
                           "Let's not overload the server (10 maximum language versions allowed per file).")
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

        # upload new project metadata
        try:
            if session["new_project"]["type"] != "tv series":
                db.execute("INSERT INTO projects (type, title, author, year, user_id, line_count) \
                           VALUES (:type, :title, :author, :year, :user_id, :line_count)",
                           type=session["new_project"]["type"], title=session["new_project"]["title"],
                           author=session["new_project"]["author"], year=session["new_project"]["year"],
                           user_id=session["user_id"], line_count=session["new_project"]["line_count"])
            else:
                db.execute("INSERT INTO projects (type, title, author, year, user_id, line_count, season, episode) \
                           VALUES (:type, :title, :author, :year, :user_id, :line_count, :season, :episode)",
                           type=session["new_project"]["type"], title=session["new_project"]["title"],
                           author=session["new_project"]["author"], year=session["new_project"]["year"],
                           user_id=session["user_id"], line_count=session["new_project"]["line_count"],
                           season=session["new_project"]["season"], episode=session["new_project"]["episode"])

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
        # make the lines 1-indexed
        for i in range(session["new_project"]["number_of_versions"]):
            for index, line in enumerate(session["new_project"]["lines"][i]):
                try:
                    db.execute("INSERT INTO lines (project_id, version_id, line_index, line) \
                               VALUES (:project_id, :version_id, :line_index, :line)",
                               project_id=session["new_project"]["project_id"],
                               version_id=version_ids[i], line_index=(index + 1), line=line)
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
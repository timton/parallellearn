#login route
@app.route("/log_in", methods=["GET", "POST"])
def log_in():
    """Log user in."""

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

        # close second window, if popped up (save/edit/rate)
        next = (session['next'].split("/"))[-1]
        if next == 'edit_line' or next == 'save_progress':
            print("adsjnfhbnjdmasklaaaaaaaaaaaaaaaaaaaaaaaaa")

        # redirect to desired page or home-page
        return redirect(url_for('index'))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:

        # forget any user_id
        session.clear()

        # save the next arg
        session['next'] = request.args.get('next')

        return render_template("login.html")
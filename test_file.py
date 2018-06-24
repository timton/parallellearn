#query all
all_versions = Version.query.all()

# order & limit
new_versions = Version.query.order_by(Version.id.desc()).limit(5).all()
comments = Comment.query.order_by(Comment.id.desc()).all()
remaining_versions = Version.query.filter(Version.project_id == version.project_id)
                                  .order_by(Version.timestamp.asc()).all()

# filter
rows = Version.query.filter(Version.id == from_version_id).all()
rows = Version.query.filter(and_(Version.project_id == project_id,
                                 Version.id == from_version_id)).all()
rows = Project.query.filter(or_(User.name == 'leela', User.fullname == 'leela dharan')).all()

rows = Project.query.filter_by(id=version.project_id).all()
rows = Project.query.filter_by(id=version.project_id).filter_by(username=version.username).all()
rows = Project.query.filter(User.name == 'leela').filter(User.fullname == 'leela dharan')

# insert
user = User(email=request.form.get("email"),
       username=request.form.get("username"),
       hash=pwd_context.hash(request.form.get("password")))
db.session.add(user)
db.session.commit()

# update
Project.query.filter(Project.id == project_id).update({"poster": postername})
Version.query.filter(Version.id == from_version_id)
             .update({"language": to_version,
                      "source": source})

# delete
User.query.filter(User.id == 2).delete()
db.session.commit()

# multiple lines
subkeyword = (
    Session.query(
        Subkeyword.subkeyword_id,
        Subkeyword.subkeyword_word
    )
    .filter_by(subkeyword_company_id=self.e_company_id)
    .filter_by(subkeyword_word=subkeyword_word)
    .filter_by(subkeyword_active=True)
    .one()
)

# configure database models
class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

class Correction(db.Model):
    __tablename__ = 'corrections'

    id = db.Column(db.Integer, primary_key=True)
    line_id = db.Column(db.Integer, nullable=False)
    correction = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    project_id = db.Column(db.Integer, nullable=False)
    version_id = db.Column(db.Integer, nullable=False)
    context_line_id = db.Column(db.Integer, nullable=False)

class Line(db.Model):
    __tablename__ = 'lines'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, nullable=False)
    version_id = db.Column(db.Integer, nullable=False)
    line_index = db.Column(db.Integer, nullable=False)
    line = db.Column(db.Text, nullable=False)

class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Text, nullable=False)
    title = db.Column(db.Text, nullable=False)
    author = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    line_count = db.Column(db.Integer, nullable=False)
    season = db.Column(db.Integer, nullable=False)
    episode = db.Column(db.Integer, nullable=False)
    poster = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)

class Rating(db.Model):
    __tablename__ = 'ratings'

    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    rating = db.Column(db.Integer, nullable=False)

class Resumable(db.Model):
    __tablename__ = 'resumables'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    current_line_id = db.Column(db.Integer, nullable=False)
    project_id = db.Column(db.Integer, nullable=False)
    from_version_id = db.Column(db.Integer, nullable=False)
    to_version_id = db.Column(db.Integer, nullable=False)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, nullable=False)
    username = db.Column(db.Text, nullable=False)
    hash = db.Column(db.Text, nullable=False)

class Version(db.Model):
    __tablename__ = 'versions'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    language = db.Column(db.Text, nullable=False)
    source = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    rating = db.Column(db.Float, nullable=False)

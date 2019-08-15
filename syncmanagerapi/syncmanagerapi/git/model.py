from datetime import datetime
import uuid

from ..database import db, ma


class GitRepo(db.Model):
    __tablename__ = "git_repos"
    id = db.Column(db.String(36), primary_key=True)
    repo_name = db.Column(db.String(100), nullable=False)
    server_path_rel = db.Column(db.Text(), nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow())
    updated = db.Column(db.DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow())

    @staticmethod
    def git_repo_by_id(_id):
        return GitRepo.query.filter_by(id=_id)

    @staticmethod
    def add_git_repo(_repo_name, _server_path_rel):
        _id = uuid.uuid4()
        new_git = GitRepo(id=_id, server_path_rel=_server_path_rel, repo_name=_repo_name)
        db.session.add(new_git)
        db.session.commit()

    def __repr__(self):
        return '<GitRepo %r>' % self.repo_id


class GitRepoSchema(ma.ModelSchema):
    class Meta:
        model = GitRepo
        sqla_session = db.session


"""
class UserGitRepos(db.Model):
    __tablename__ = "user_git_repos"
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    repo_id = db.Column(db.String(36), db.ForeignKey('git_repos.id'))
    local_path_rel = db.Column(db.Text(), unique=True, nullable=False)
    client_id = db.Column(db.String(100), unique=True, nullable=False) # identifies users machine
    # people = Person.query.order_by(Person.lname).all()
"""

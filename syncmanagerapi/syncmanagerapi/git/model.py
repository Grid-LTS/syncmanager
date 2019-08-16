from datetime import datetime
import uuid

from ..database import db, ma
from ..model import User


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
    def add_git_repo(_repo_name, _server_path_rel, _user_id, _local_path_rel, _client_id='default'):
        _id = uuid.uuid4()
        _assoc_id = uuid.uuid4()
        new_git = GitRepo(id=_id, server_path_rel=_server_path_rel, repo_name=_repo_name)
        user_gitrepo_assoc = UserGitReposAssoc(id=_assoc_id, user_id=_user_id, local_path_rel=_local_path_rel,
                                               client_id=_client_id)
        new_git.users.append(user_gitrepo_assoc)
        db.session.add(new_git)
        db.session.commit()
        return new_git

    def __repr__(self):
        return '<GitRepo %r>' % self.repo_id


class GitRepoSchema(ma.ModelSchema):
    class Meta:
        model = GitRepo
        sqla_session = db.session


class UserGitReposAssoc(db.Model):
    __tablename__ = "user_git_repos"
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    repo_id = db.Column(db.String(36), db.ForeignKey('git_repos.id'))
    local_path_rel = db.Column(db.Text(), nullable=False)
    client_id = db.Column(db.String(100), nullable=False)  # identifies users machine
    git_repo = db.relationship(GitRepo, backref="users")
    user = db.relationship(User, backref="gitrepos")

    @staticmethod
    def add_user_gitrepo_assoc(_user_id, _repo_id, _local_path_rel, _client_id='default'):
        """
        sets an entry in the association table. This should only be used when associating an existing repository to 
        another the user, given by id. When creating the repo in the database do not use this function, but create an
        UserGitRepoAssoc object and pass it to the GitRepo dto before committing to the DB session
        :param _user_id: id of the user
        :param _repo_id: id of the git repo (should already be existing in the DB)
        :param _local_path_rel: local path on the users machine
        :param _client_id: name of the users machine
        :return: 
        """
        _id = uuid.uuid4()
        new_gitrep_assoc = UserGitReposAssoc(id=_id, user_id=_user_id, repo_id=_repo_id, local_path_rel=
        _local_path_rel, client_id=_client_id)
        db.session.add(new_gitrep_assoc)
        db.session.commit()
        return new_gitrep_assoc


class UserGitReposAssocSchema(ma.ModelSchema):
    class Meta:
        model = UserGitReposAssoc
        sqla_session = db.session
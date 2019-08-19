from datetime import datetime
import os.path as osp
import uuid

from ..database import db, ma
from ..model import User
from marshmallow import fields


class GitRepo(db.Model):
    __tablename__ = "git_repos"
    id = db.Column(db.String(36), primary_key=True)
    server_path_rel = db.Column(db.Text(), nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow())
    updated = db.Column(db.DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow())
    user_id = None

    def __init__(self, server_path_rel, user_id):
        if server_path_rel[-4:] != '.git':
            server_path_rel += '.git'
        self.server_path_rel = osp.join(user_id, server_path_rel)
        self.user_id = user_id

    @staticmethod
    def git_repo_by_id(_id):
        return GitRepo.query.filter_by(id=_id)

    def add(self, _local_path_rel, _remote_name, _client_id='default'):
        return GitRepo.persist_git_repo(self, _local_path_rel=_local_path_rel, _remote_name=_remote_name,
                                        _client_id=_client_id)

    @staticmethod
    def add_git_repo(_server_path_rel, _user_id, _local_path_rel, _client_id='default'):
        git_repo = GitRepo(server_path_rel=_server_path_rel, user_id=_user_id)
        return GitRepo.persist_git_repo(git_repo, _local_path_rel=_local_path_rel, _client_id=_client_id)

    @staticmethod
    def persist_git_repo(git_repo_obj, _local_path_rel, _remote_name, _client_id='default'):
        result = GitRepo.query.outerjoin(UserGitReposAssoc) \
            .filter(GitRepo.server_path_rel == git_repo_obj.server_path_rel) \
            .filter(UserGitReposAssoc.user_id == git_repo_obj.user_id) \
            .one_or_none()
        if not result:
            _id = uuid.uuid4()
            _assoc_id = uuid.uuid4()
            git_repo_obj.id = _id
            user_gitrepo_assoc = UserGitReposAssoc(id=_assoc_id, user_id=git_repo_obj.user_id,
                                                   local_path_rel=_local_path_rel,
                                                   remote_name=_remote_name,
                                                   client_id=_client_id)
            git_repo_obj.userinfo.append(user_gitrepo_assoc)
            db.session.add(git_repo_obj)
            db.session.commit()
        else:
            git_repo_obj = result
        return git_repo_obj

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
    remote_name = db.Column(db.String(100), nullable=False)  # name of remote
    client_id = db.Column(db.String(100), nullable=False)  # identifies users machine
    git_repo = db.relationship(GitRepo, backref="userinfo")
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
        new_gitrep_assoc = UserGitReposAssoc(id=_id, user_id=_user_id, repo_id=_repo_id,
                                             local_path_rel=_local_path_rel, client_id=_client_id)
        db.session.add(new_gitrep_assoc)
        db.session.commit()
        return new_gitrep_assoc

    @staticmethod
    def get_user_repos_by_client_id(_user_id, _client_id):
        return UserGitReposAssoc.query.filter_by(user_id=_user_id, client_id=_client_id).all()


class UserGitReposAssocSchema(ma.ModelSchema):
    class Meta:
        model = UserGitReposAssoc
        sqla_session = db.session


class UserGitReposAssocFullSchema(UserGitReposAssocSchema):
    git_repo = fields.Nested(GitRepoSchema, default={}, many=False)


class GitRepoFullSchema(ma.ModelSchema):
    class Meta:
        model = GitRepo
        sqla_session = db.session

    userinfo = fields.Nested(UserGitReposAssocSchema, default=[], many=True)

from datetime import datetime
import os.path as osp
import uuid

from ..database import db, ma
from .git import GitRepoFs
from ..model import User, ClientEnv, ClientEnvSchema
from ..error import DataInconsistencyException
from marshmallow import fields


class GitRepo(db.Model):
    __tablename__ = "git_repos"
    id = db.Column(db.String(36), primary_key=True)
    server_path_rel = db.Column(db.Text(), nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow())
    updated = db.Column(db.DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow())
    user_id = None

    def __init__(self, server_path_rel, user_id):
        self.server_path_rel = GitRepo.get_server_path_rel(server_path_rel, user_id)
        self.user_id = user_id

    @property
    def server_path_absolute(self):
        return GitRepoFs.get_bare_repo_fs_path(self.server_path_rel)

    @staticmethod
    def get_server_path_rel(server_path_rel, user_id):
        if server_path_rel[-4:] != '.git':
            server_path_rel += '.git'
        return osp.join(user_id, server_path_rel)

    @staticmethod
    def get_repo_by_id(_id):
        return GitRepo.query.filter_by(id=_id).one_or_none()

    @staticmethod
    def get_repo_by_id_and_user_id(_id, _user_id):
        return GitRepo.query.outerjoin(UserGitReposAssoc) \
            .filter(UserGitReposAssoc.user_id == _user_id) \
            .filter(GitRepo.id == _id) \
            .one_or_none()

    @staticmethod
    def load_by_server_path(_server_path_rel):
        return GitRepo.query.filter_by(server_path_rel=_server_path_rel).one_or_none()

    def add(self, _local_path_rel, _remote_name, _client_envs):
        git_repo, new_reference = GitRepo.persist_git_repo(self, _local_path_rel=_local_path_rel,
                                                           _remote_name=_remote_name,
                                                           _client_envs=_client_envs)
        return new_reference

    def remove(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def add_git_repo(_server_path_rel, _user_id, _local_path_rel, _remote_name, _client_envs):
        git_repo = GitRepo.query.filter_by(server_path_rel=_server_path_rel).one_or_none()
        if not git_repo:
            git_repo = GitRepo(server_path_rel=_server_path_rel, user_id=_user_id)
        return GitRepo.persist_git_repo(git_repo, _local_path_rel=_local_path_rel, _remote_name=_remote_name,
                                        _client_envs=_client_envs)

    @staticmethod
    def persist_git_repo(git_repo_obj, _local_path_rel, _remote_name, _client_envs):
        result = GitRepo.query.outerjoin(UserGitReposAssoc) \
            .filter(GitRepo.server_path_rel == git_repo_obj.server_path_rel) \
            .filter(UserGitReposAssoc.user_id == git_repo_obj.user_id) \
            .one_or_none()
        # if the repo is referenced by an association, it is not again referenced in order to avoid conflicts
        # therefore no filtering by _local_path_rel since this would dismiss other local references
        # no filtering by client_env: client env just multiplies the reference on the to a different machine but does
        # not imply a unique new reference in which we are interested in
        if not result:
            if not _client_envs:
                raise DataInconsistencyException('No client env given')
            _assoc_id = str(uuid.uuid4())
            if not git_repo_obj.id:
                git_repo_obj.id = str(uuid.uuid4())
            user_gitrepo_assoc = UserGitReposAssoc(id=_assoc_id, user_id=git_repo_obj.user_id,
                                                   local_path_rel=_local_path_rel,
                                                   remote_name=_remote_name,
                                                   client_envs=_client_envs)
            git_repo_obj.userinfo.append(user_gitrepo_assoc)
            db.session.add(git_repo_obj)
            db.session.commit()
            new_reference = True
        else:
            new_reference = False
            git_repo_obj = result
        return git_repo_obj, new_reference

    def __repr__(self):
        return '<GitRepo %r>' % self.repo_id


class GitRepoSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = GitRepo
        sqla_session = db.session
        include_relationships = True

    server_path_absolute = fields.String()


# identifies the user's client environments
# an environment allows to fine-grainly select what data is synced on the client machine
user_clientenv_gitrepo_table = db.Table('user_gitrepo_clientenv', db.Model.metadata,
                                        db.Column('user_gitrepo_assoc_id', db.String(36),
                                                  db.ForeignKey('user_git_repos.id', ondelete='CASCADE'), nullable=False),
                                        db.Column('user_clientenv_id', db.String(36),
                                                  db.ForeignKey('user_client_env.id', ondelete='CASCADE'), nullable=False)
                                        )


class UserGitReposAssoc(db.Model):
    __tablename__ = "user_git_repos"
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id', ondelete='CASCADE'))
    repo_id = db.Column(db.String(36), db.ForeignKey('git_repos.id', ondelete='CASCADE'))
    local_path_rel = db.Column(db.Text(), nullable=False)
    remote_name = db.Column(db.String(100), nullable=False)  # name of remote
    user = db.relationship(User, backref=db.backref("gitrepos", passive_deletes=True))
    client_envs = db.relationship(ClientEnv,
                                  secondary=user_clientenv_gitrepo_table)

    @staticmethod
    def add_user_gitrepo_assoc(_user_id, _repo_id, _local_path_rel, _client_envs):
        """
        sets an entry in the association table. This should only be used when associating an existing repository to 
        another the user, given by id. When creating the repo in the database do not use this function, but create an
        UserGitRepoAssoc object and pass it to the GitRepo dto before committing to the DB session
        :param _user_id: id of the user
        :param _repo_id: id of the git repo (should already be existing in the DB)
        :param _local_path_rel: local path on the users machine
        :param _client_envs: list of db entities for the client environments of the user
        :return: 
        """
        if not _client_envs:
            raise DataInconsistencyException('No client environment given')
        _id = uuid.uuid4()
        new_gitrep_assoc = UserGitReposAssoc(id=str(_id), user_id=_user_id, repo_id=_repo_id,
                                             local_path_rel=_local_path_rel)
        new_gitrep_assoc.client_envs.extend(_client_envs)
        db.session.add(new_gitrep_assoc)
        db.session.commit()
        return new_gitrep_assoc

    def remove(self):
        db.session.delete(self)
        db.session.commit()
    
    @staticmethod
    def query_gitrepo_assoc_by_user_id_and_repo_id_and_local_path(_user_id, _repo_id, _local_path_rel):
        return UserGitReposAssoc.query.filter_by(user_id=_user_id, repo_id=_repo_id,
                                                 local_path_rel=_local_path_rel).first()
    

    @staticmethod
    def get_user_repos_by_client_env_name(_user_id, _client_env_name):
        return UserGitReposAssoc.query.join(UserGitReposAssoc.client_envs).filter_by(user_id=_user_id) \
            .filter(ClientEnv.env_name == _client_env_name).all()

    @staticmethod
    def get_user_repos(_user_id):
        return UserGitReposAssoc.query.add_columns(ClientEnv.env_name).join(UserGitReposAssoc.client_envs) \
            .filter_by(user_id=_user_id).all()

# backreference so that there is a cascading on deletion
GitRepo.userinfo = db.relationship(UserGitReposAssoc, cascade="all, delete", backref=db.backref("git_repo"), passive_deletes=True)

# Marshmallow schemas
class UserGitReposAssocSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = UserGitReposAssoc
        sqla_session = db.session
        include_relationships = True


class UserGitReposAssocFullSchema(UserGitReposAssocSchema):
    git_repo = fields.Nested(GitRepoSchema, default={}, many=False)
    client_envs = fields.Nested(ClientEnvSchema, default=[], many=True)


class GitRepoFullSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = GitRepo
        sqla_session = db.session
        include_relationships = True

    server_path_absolute = fields.String()
    userinfo = fields.Nested(UserGitReposAssocFullSchema, default=[], many=True)

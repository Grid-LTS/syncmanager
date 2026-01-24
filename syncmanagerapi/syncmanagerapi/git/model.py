import os.path as osp
import uuid
from datetime import datetime, timezone
from pathlib import PurePosixPath, Path

from dateutil.relativedelta import relativedelta
from flask import current_app
from marshmallow import fields
from sqlalchemy import or_

from ..database import db, ma
from ..domain import DatabaseConflict, DataInconsistencyException
from ..model import User, ClientEnv


def get_bare_repo_fs_path(server_path_relative: PurePosixPath):
    fs_root_dir = current_app.config['FS_ROOT']
    return osp.join(osp.join(fs_root_dir, 'git'), Path(*server_path_relative.parts))


class GitRepo(db.Model):
    __tablename__ = "git_repos"
    id = db.Column(db.String(36), primary_key=True)
    server_path_rel = db.Column(db.Text(), nullable=False)
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    last_commit_date = db.Column(db.DateTime, nullable=True)
    user_id = None

    def __init__(self, server_path_rel: PurePosixPath, user_id):
        self.server_path_rel = GitRepo.get_server_path_rel(server_path_rel, user_id)
        self.user_id = user_id

    def add(self, _local_path_rel, _remote_name, _client_envs, _git_config_user=None,
            _git_config_email=None):
        # check first if the repo is already registered
        result = GitRepo.query.outerjoin(UserGitReposAssoc) \
            .filter(GitRepo.server_path_rel == self.server_path_rel) \
            .filter(UserGitReposAssoc.user_id == self.user_id) \
            .one_or_none()
        # if the repo is referenced by an association aka clientrepo, it is not again referenced in order to avoid conflicts
        # therefore no filtering by _local_path_rel since this would dismiss other local references
        # no filtering by client_env: client env just multiplies the reference to a different machine but does
        # not imply a unique new reference in which we are interested in.
        # only filter by user id, to make sure that this  is a unique new server repo and local repo for the current user
        if not result:
            assoc_id = str(uuid.uuid4())
            user_gitrepo_assoc = UserGitReposAssoc.create_user_gitrepo_assoc(
                _id=assoc_id,
                _user_id=self.user_id,
                _local_path_rel=_local_path_rel,
                _remote_name=_remote_name,
                _client_envs=_client_envs,
                _git_config_user=_git_config_user,
                _git_config_email=_git_config_email)
            self._persist(user_gitrepo_assoc)
            new_reference = True
        else:
            new_reference = False
        return new_reference

    def _persist(self, _git_user_repo_assoc):
        if not _git_user_repo_assoc.client_envs:
            raise DataInconsistencyException('No client env given')
        if not self.id:
            self.id = str(uuid.uuid4())
        self.userinfo.append(_git_user_repo_assoc)
        db.session.add(self)
        db.session.commit()

    def remove_client_env_from_repo(self, client_env):
        # find the reference to git repo for this user
        for ind, user_info in enumerate(self.userinfo):
            remaining_client_env = [env for env in user_info.client_envs if env.env_name != client_env]
            if not remaining_client_env:
                if len(self.userinfo) == 1:
                    raise DatabaseConflict(f"The server repo {self.server_path_rel} must be referenced by at "
                                           f"least one sync environment")
                user_info.remove()
                return
            user_info.remove_from_clientenv(client_env)
            user_info.client_envs = remaining_client_env
            db.session.add(user_info)
            db.session.commit()

    def remove(self):
        db.session.delete(self)
        db.session.commit()

    @property
    def server_path_absolute(self):
        return get_bare_repo_fs_path(PurePosixPath(self.server_path_rel))

    @staticmethod
    def get_server_path_rel(_server_path_rel: PurePosixPath, user_id) -> str:
        server_path_rel = str(_server_path_rel)
        if server_path_rel[-4:] != '.git':
            server_path_rel += '.git'
        return str(PurePosixPath(user_id) / server_path_rel)

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
    def get_repos_by_sync_env_and_user_id(_user_id, _env_name):
        return GitRepo.query.outerjoin(UserGitReposAssoc) \
            .outerjoin(UserGitReposAssoc.client_envs) \
            .filter(UserGitReposAssoc.user_id == _user_id) \
            .filter(ClientEnv.env_name == _env_name) \
            .all()

    @staticmethod
    def get_repos_by_namespace_and_user_id(namespace, _user_id):
        if not namespace:
            return []
        try:
            uuid.UUID(namespace.split('/')[0])
        except ValueError:
            namespace = str(PurePosixPath(_user_id) / namespace)
        return GitRepo.query.filter(GitRepo.server_path_rel.like(namespace + '%')) \
            .all()

    @staticmethod
    def load_by_server_path(_server_path_rel):
        return GitRepo.query.filter_by(server_path_rel=_server_path_rel).one_or_none()

    @staticmethod
    def add_git_repo(_server_path_rel, _user_id, _local_path_rel, _remote_name, _client_envs, _git_config_user=None,
                     _git_config_email=None):
        git_repo = GitRepo.query.filter_by(server_path_rel=_server_path_rel).one_or_none()
        if not git_repo:
            git_repo = GitRepo(server_path_rel=_server_path_rel, user_id=_user_id)
        new_reference = git_repo.add(_local_path_rel=_local_path_rel, _remote_name=_remote_name,
                                     _client_envs=_client_envs, _git_config_user=_git_config_user,
                                     _git_config_email=_git_config_email)
        return git_repo, new_reference

    def __repr__(self):
        return '<GitRepo %r>' % self.repo_id


class GitRepoSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = GitRepo
        sqla_session = db.session
        include_relationships = True

    server_path_absolute = fields.String()
    last_commit_date = fields.DateTime()


# identifies the user's client environments
# an environment allows to fine-grainly select what data is synced on the client machine
user_clientenv_gitrepo_table = db.Table('user_gitrepo_clientenv', db.Model.metadata,
                                        db.Column('user_gitrepo_assoc_id', db.String(36),
                                                  db.ForeignKey('user_git_repos.id', ondelete='CASCADE'),
                                                  nullable=False),
                                        db.Column('user_clientenv_id', db.String(36),
                                                  db.ForeignKey('user_client_env.id', ondelete='CASCADE'),
                                                  nullable=False)
                                        )


class UserGitReposAssoc(db.Model):
    __tablename__ = "user_git_repos"
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    repo_id = db.Column(db.String(36), db.ForeignKey('git_repos.id', ondelete='CASCADE'), nullable=False)
    local_path_rel = db.Column(db.Text(), nullable=False)
    remote_name = db.Column(db.String(100), nullable=False)  # name of remote git repo
    user_name_config = db.Column(db.String(50), nullable=True)
    user_email_config = db.Column(db.String(100), nullable=True)
    # Todo move this relationship to User entity as deletion might not work with every DB engine
    user = db.relationship(User, backref=db.backref("gitrepos", passive_deletes=True))
    client_envs = db.relationship(ClientEnv,
                                  secondary=user_clientenv_gitrepo_table)

    @property
    def clientenvs(self):
        return [env.env_name for env in self.client_envs]

    @staticmethod
    def create_user_gitrepo_assoc(_user_id, _local_path_rel, _remote_name, _client_envs,
                                  _repo_id=None,  # can be set by foreign key relation when persisting sqlalchemy
                                  _id=None,
                                  _git_config_user=None,
                                  _git_config_email=None):
        if not _client_envs:
            raise DataInconsistencyException('No client environment given')
        if not _id:
            _id = uuid.uuid4()
        new_gitrep_assoc = UserGitReposAssoc(id=str(_id), user_id=_user_id,
                                             repo_id=_repo_id,
                                             local_path_rel=_local_path_rel,
                                             remote_name=_remote_name,
                                             user_name_config=_git_config_user,
                                             user_email_config=_git_config_email)
        new_gitrep_assoc.client_envs.extend(_client_envs)
        return new_gitrep_assoc

    @staticmethod
    def add_user_gitrepo_assoc(_user_id, _repo_id, _local_path_rel, _remote_name, _client_envs):
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
        new_gitrep_assoc = UserGitReposAssoc.create_user_gitrepo_assoc(_user_id, _repo_id, _local_path_rel,
                                                                       _remote_name, _client_envs)
        db.session.add(new_gitrep_assoc)
        db.session.commit()
        return new_gitrep_assoc

    def remove_from_clientenv(self, _env_name: str):
        client_env = ClientEnv.get_client_env(_user_id=self.user_id, _env_name=_env_name)
        self.remove_from_client_env(client_env)

    def remove_from_client_env(self, _client_env: ClientEnv):
        if not _client_env:
            return
        if len(self.clientenvs) == 1 and self.clientenvs[0] == _client_env.env_name:
            self.remove()
            return
        if not _client_env.env_name in self.clientenvs:
            return
        self.client_envs.remove(_client_env)
        db.session.add(self)
        db.session.commit()

    def remove(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def query_gitrepo_assoc_by_id(_client_repo_id):
        return UserGitReposAssoc.query.filter_by(id=_client_repo_id).one_or_none()

    @staticmethod
    def query_gitrepo_assoc_by_user_id_and_repo_id_and_local_path(_user_id, _repo_id, _local_path_rel):
        return UserGitReposAssoc.query.filter_by(user_id=_user_id, repo_id=_repo_id,
                                                 local_path_rel=_local_path_rel).first()

    @staticmethod
    def get_user_repos_by_client_env_name(_user_id, _env_name):
        return UserGitReposAssoc.query.join(UserGitReposAssoc.client_envs).filter_by(user_id=_user_id) \
            .filter(ClientEnv.env_name == _env_name).all()

    @staticmethod
    def get_user_repos_by_client_env_name_and_retention(_user_id, _client_env_name, _retention_years, _refresh_rate):
        retention_date = datetime.now() - relativedelta(years=_retention_years)
        return (UserGitReposAssoc.query
                .join(UserGitReposAssoc.client_envs)
                .join(GitRepo, UserGitReposAssoc.repo_id == GitRepo.id)
                .filter(UserGitReposAssoc.user_id == _user_id) \
                .filter(ClientEnv.env_name == _client_env_name)
                .filter(or_(
            GitRepo.last_commit_date >= retention_date,
            GitRepo.last_commit_date == None,
            GitRepo.updated <= datetime.now() - relativedelta(months=_refresh_rate)
        )).all())

    @staticmethod
    def get_user_repos(_user_id):
        return UserGitReposAssoc.query.add_columns(ClientEnv.env_name).join(UserGitReposAssoc.client_envs) \
            .filter_by(user_id=_user_id).all()


# backreference so that there is a cascading on deletion
GitRepo.userinfo = db.relationship(UserGitReposAssoc, cascade="all, delete", backref=db.backref("git_repo"))


# Marshmallow schemas
class UserGitReposAssocSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = UserGitReposAssoc
        sqla_session = db.session
        include_relationships = True
        exclude = ('client_envs',)

    clientenvs = fields.List(attribute="clientenvs", cls_or_instance=fields.Str())


class UserGitReposAssocFullSchema(UserGitReposAssocSchema):
    git_repo = fields.Nested(GitRepoSchema, dump_default={}, load_default={}, many=False)


class GitRepoFullSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = GitRepo
        sqla_session = db.session
        include_relationships = True

    server_path_absolute = fields.String()
    last_commit_date = fields.DateTime()
    userinfo = fields.Nested(UserGitReposAssocFullSchema, dump_default=[], load_default=[], many=True)

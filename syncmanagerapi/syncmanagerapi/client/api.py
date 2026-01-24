import os

from flask import request, Response

from ..domain import DatabaseConflict
from ..error import InvalidRequest

from ..auth import login_required
from ..git.model import UserGitReposAssoc, GitRepo


def create_syncdir():
    body = request.data
    if not body:
        raise InvalidRequest('Provide target directory path \'target_dir\' payload', 'target_dir')
    data = request.get_json(force=True)
    if not data['target_dir']:
        raise InvalidRequest('Provide target directory path \'target_dir\' payload', 'target_dir')
    target_dir = data['target_dir']
    if not os.path.exists(target_dir):
        try:
            oldmask = os.umask(0o002)
            os.makedirs(target_dir)
            os.umask(oldmask)
        except PermissionError:
            raise InvalidRequest('No permissions to create resource {}'.format(target_dir), 'target_dir', 403)
    return Response(status=204)


@login_required
def get_all_client_envs():
    from ..decorators import requires_auth
    from ..model import User, ClientEnv, ClientEnvSchema
    requires_auth()
    auth = request.authorization
    user = User.user_by_username(auth['username'])
    schema = ClientEnvSchema(many=True)
    client_envs = ClientEnv.get_client_envs(_user_id=user.id)
    return schema.dump(client_envs)


@login_required
def add_client_env():
    from ..decorators import requires_auth
    from ..model import User, ClientEnv
    requires_auth()
    auth = request.authorization
    user = User.user_by_username(auth['username'])
    body = request.data
    if not body:
        raise InvalidRequest('Provide descriptor for the client environment', 'env_name')
    data = request.get_json(force=True)
    if not data['env_name']:
        raise InvalidRequest('Provide descriptor for the client environment', 'env_name')
    ClientEnv.add_client_env(_user_id=user.id, _env_name=data['env_name'],
                             _filesystem_root_dir=data.get('filesystem_root_dir', None))
    return Response(status=204)


@login_required
def update_client_env(env_name):
    from ..decorators import requires_auth
    from ..model import User, ClientEnv, ClientEnvSchema
    from ..database import db
    requires_auth()
    auth = request.authorization
    user = User.user_by_username(auth['username'])
    body = request.data
    if not body:
        raise InvalidRequest('Provide update body for the client environment', 'payload')
    data = request.get_json(force=True)
    if not data['env_name']:
        raise InvalidRequest('Provide descriptor for the client environment', 'env_name')
    if data['env_name'] != env_name:
        raise InvalidRequest('Client environment name cannot be changed', 'env_name')
    client_env = ClientEnv.get_client_env(_user_id=user.id, _env_name=env_name)
    client_env.filesystem_root_dir = data['filesystem_root_dir']
    db.session.add(client_env)
    db.session.commit()
    schema = ClientEnvSchema()
    return schema.dump(client_env)


@login_required
def delete_client_env(env_name):
    from ..decorators import requires_auth
    from ..model import User, ClientEnv
    requires_auth()
    auth = request.authorization
    user = User.user_by_username(auth['username'])
    client_env = ClientEnv.get_client_env(_user_id=user.id, _env_name=env_name)
    if not client_env:
        return Response(status=204)
    # Todo introduce abstraction as soon as more sync tools are onboarded
    git_repos = GitRepo.get_repos_by_sync_env_and_user_id(_user_id=user.id, _env_name=env_name)
    if not git_repos:
        # should'nt be possible, but if we need to clean up orphaned references
        user_git_repos = UserGitReposAssoc.get_user_repos_by_client_env_name(_user_id=user.id, _env_name=env_name)
        try:
            for user_git_repo in user_git_repos:
                user_git_repo.remove_from_client_env(client_env)
        except DatabaseConflict as e:
            return Response(response=e.message, status=409)
    else:
        for git_repo in git_repos:
            git_repo.remove_client_env_from_repo(env_name)
    client_env.remove()
    return Response(status=204)

import os

from flask import request, Response
from ..error import InvalidRequest

from ..auth import login_required


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
        raise InvalidRequest('Provide update body for the client environment')
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

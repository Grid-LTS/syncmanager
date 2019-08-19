import os

from flask import request, Response
from ..error import InvalidRequest


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


def add_client_env():
    from ..decorators import requires_auth
    from ..model import User, ClientEnv
    requires_auth()
    auth = request.authorization
    user = User.user_by_username(auth['username'])
    body = request.data
    if not body:
        raise InvalidRequest('Provide descriptor for the client environment', 'client_env_name')
    data = request.get_json(force=True)
    if not data['client_env_name']:
        raise InvalidRequest('Provide descriptor for the client environment', 'client_env_name')
    client_env_name = data['client_env_name']
    ClientEnv.add_client_env(_user_id=user.id, _env_name=client_env_name)
    return Response(status=204)

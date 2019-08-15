from flask import current_app, request, Response
from ..error import InvalidRequest


def create_repo():
    from .model import GitRepo
    body = request.data
    from ..decorators import requires_auth
    requires_auth()
    auth = request.authorization
    if not body:
        raise InvalidRequest('Empty body', 'repo_name')
    data = request.get_json(force=True)
    repo_name = data['repo_name']
    if data.get('server_path_relative', None):
        server_path_rel = data['server_path_relative']
    else:
        server_path_rel = f"{repo_name}.git"
    GitRepo.add_git_repo(_repo_name=repo_name, _server_path_rel=server_path_rel)
    return Response(status=204)

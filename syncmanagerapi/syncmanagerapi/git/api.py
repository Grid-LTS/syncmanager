from flask import current_app, request, Response
from ..error import InvalidRequest


def create_repo():
    from .model import GitRepo, GitRepoSchema
    from ..model import User
    body = request.data
    from ..decorators import requires_auth
    requires_auth()
    auth = request.authorization
    if not body:
        raise InvalidRequest('Empty body', 'repo_name')
    user = User.user_by_username(auth['username'])
    data = request.get_json(force=True)
    repo_name = data['repo_name']
    if data.get('server_path_relative', None):
        server_path_rel = data['server_path_relative']
    else:
        server_path_rel = f"{repo_name}.git"
    gitrepo = GitRepo.add_git_repo(_repo_name=repo_name, _server_path_rel=server_path_rel, _user_id=user.id,
                                   _local_path_rel="home/code", _client_id="home")
    gitrepo_schema = GitRepoSchema()
    return gitrepo_schema.dump(gitrepo).data


def get_repos():
    from .model import UserGitReposAssocSchema
    from ..model import User
    from ..decorators import requires_auth
    requires_auth()
    auth = request.authorization
    user = User.user_by_username(auth['username'])
    user_gitrepo_assoc_schema = UserGitReposAssocSchema(many=True)
    return user_gitrepo_assoc_schema.dump(user.gitrepos).data

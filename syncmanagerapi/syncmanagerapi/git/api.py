import os.path as osp
from .git import GitRepoFs
from flask import current_app, request, Response
from ..error import InvalidRequest


def create_repo():
    from .model import GitRepo, GitRepoSchema
    from ..model import User
    body = request.data
    from ..decorators import requires_auth
    requires_auth()
    auth = request.authorization
    user = User.user_by_username(auth['username'])
    if not body:
        raise InvalidRequest('Empty body', 'local_path')
    data = request.get_json(force=True)
    if not 'local_path' in data or not data['local_path']:
        raise InvalidRequest('Empty body', 'local_path')
    local_path = data['local_path']
    if 'server_repo_name' in data:
        repo_name = data['server_repo_name']
    else:
        repo_name = osp.basename(local_path)
    if repo_name[-4:] != '.git':
        repo_name += '.git'
    if data.get('server_parent_dir_relative', None):
        server_parent_dir_rel = data['server_parent_dir_relative']
    else:
        server_parent_dir_rel = ""
    server_path_rel = osp.join(server_parent_dir_rel, repo_name)
    gitrepo_entity = GitRepo(server_path_rel=server_path_rel, user_id=user.id)
    fs_git_repo = GitRepoFs(gitrepo_entity)
    fs_git_repo.create_bare_repo()
    gitrepo_entity.add(_local_path_rel=local_path, _client_id="home")
    gitrepo_schema = GitRepoSchema()
    return gitrepo_schema.dump(gitrepo_entity).data


def get_repos():
    from .model import UserGitReposAssocSchema
    from ..model import User
    from ..decorators import requires_auth
    requires_auth()
    auth = request.authorization
    user = User.user_by_username(auth['username'])
    user_gitrepo_assoc_schema = UserGitReposAssocSchema(many=True)
    return user_gitrepo_assoc_schema.dump(user.gitrepos).data

import os.path as osp

from .git import GitRepoFs
from flask import current_app, jsonify, request, Response
from ..error import InvalidRequest


def create_repo():
    from ..database import db
    from .model import GitRepo, UserGitReposAssoc, GitRepoSchema
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
    if not 'remote_name' in data or not data['remote_name']:
        raise InvalidRequest('Empty body', 'remote_name')
    remote_name = data['remote_name']
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
    if data.get('client_env', None):
        client_env_name = data['client_env']
    else:
        client_env_name = 'default'
    client_env_entity = None
    for client_env in user.client_envs:
        if client_env.env_name == client_env_name:
            client_env_entity = client_env
            break
    if data.get('all_client_envs', False):
        desired_client_env_entities = user.client_envs
    else:
        desired_client_env_entities = [client_env_entity]
    server_path_rel = osp.join(server_parent_dir_rel, repo_name)
    gitrepo_entity = GitRepo.load_by_server_path(_server_path_rel=GitRepo.get_server_path_rel(server_path_rel, user.id))
    if not gitrepo_entity:
        gitrepo_entity = GitRepo(server_path_rel=server_path_rel, user_id=user.id)
    else:
        gitrepo_entity.user_id = user.id
    fs_git_repo = GitRepoFs(gitrepo_entity)
    fs_git_repo.create_bare_repo()
    new_reference = gitrepo_entity.add(_local_path_rel=local_path, _remote_name=remote_name,
                                       _client_envs=desired_client_env_entities)
    if not new_reference:
        # check that users client env is included
        gitrepo_clientinfo = UserGitReposAssoc.query_gitrepo_assoc_by_user_id(_user_id=user.id)
        if gitrepo_clientinfo:
            referenced_client_env_ids = [client_env.id for client_env in gitrepo_clientinfo.client_envs]
            # missing_client_envs = [client_env for client_env in desired_client_env_entities \
            #        if not client_env.id in referenced_client_env_ids]
            new_reference = not client_env_entity.id in referenced_client_env_ids
            if new_reference:
                gitrepo_clientinfo.client_envs.append(client_env_entity)
                db.session.add(gitrepo_clientinfo)
                db.session.commit()
                print("No new reference has been created. The existing local reference at " +
                      f"{gitrepo_clientinfo.local_path_rel} with remote " +
                      f"{remote_name} has been added to your current environment.")
            else:
                print(
                    "No new reference has been created. The existing local reference at " +
                    f"{gitrepo_clientinfo.local_path_rel} with remote " +
                    f"{remote_name} is already includes this remote repo.")
    gitrepo_schema = GitRepoSchema()
    response = gitrepo_schema.dump(gitrepo_entity)
    response['remote_repo_path'] = fs_git_repo.gitrepo_path
    response['is_new_reference'] = new_reference
    # ToDo distinguish status codes: new created or already existing
    return response


def get_repos(client_env, full_info=False):
    from .model import UserGitReposAssoc, UserGitReposAssocSchema, UserGitReposAssocFullSchema
    from ..model import User, ClientEnv
    from ..decorators import requires_auth
    requires_auth()
    auth = request.authorization
    user = User.user_by_username(auth['username'])
    client_env_entity = ClientEnv.get_client_env(_user_id=user.id, _env_name=client_env)
    if not client_env_entity:
        message = f"The client environment {client_env} does not exist for your user."
        raise InvalidRequest(message=message, field='client_env', status_code=404)
    if full_info:
        user_gitrepo_assoc_schema = UserGitReposAssocFullSchema(many=True)
    else:
        user_gitrepo_assoc_schema = UserGitReposAssocSchema(many=True)
    repos = UserGitReposAssoc.get_user_repos_by_client_env_name(_user_id=user.id, _client_env_name=client_env)
    if not repos:
        return jsonify([])
    return user_gitrepo_assoc_schema.dump(repos)

import os.path as osp
import uuid

from .git import GitRepoFs
from flask import current_app, jsonify, request, Response
from ..error import InvalidRequest


def create_repo():
    from ..database import db
    from .model import GitRepo, UserGitReposAssoc, GitRepoFullSchema
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
    if not client_env_entity:
        raise InvalidRequest(f"User has no environment with name '{client_env_name}' configured.", 'client_env')
    if data.get('all_client_envs', False):
        desired_client_env_entities = user.client_envs
    else:
        desired_client_env_entities = [client_env_entity]
    server_path_rel = osp.join(server_parent_dir_rel, repo_name)
    git_repo_entity = GitRepo.load_by_server_path(
        _server_path_rel=GitRepo.get_server_path_rel(server_path_rel, user.id))
    if not git_repo_entity:
        git_repo_entity = GitRepo(server_path_rel=server_path_rel, user_id=user.id)
    else:
        git_repo_entity.user_id = user.id
        # only on initial creation of the repo can all client environments be referenced
        desired_client_env_entities = [client_env_entity]
    fs_git_repo = GitRepoFs(git_repo_entity)
    fs_git_repo.create_bare_repo()
    new_reference = git_repo_entity.add(_local_path_rel=local_path, _remote_name=remote_name,
                                        _client_envs=desired_client_env_entities)
    if not new_reference:
        is_env_referenced = False
        git_user_repo_assoc = None
        git_user_repo_assoc_ref = None
        for user_info in git_repo_entity.userinfo:
            if user_info.local_path_rel == local_path:
                git_user_repo_assoc = user_info
            else:
                continue
            referenced_envs = [env.env_name for env in user_info.client_envs]
            if client_env_name in referenced_envs:
                is_env_referenced = True
                git_user_repo_assoc_ref = user_info
                # existing reference found, abort lookup
                break
        if not is_env_referenced:
            if git_user_repo_assoc:
                git_user_repo_assoc.client_envs.append(client_env_entity)
                db.session.add(git_user_repo_assoc)
                db.session.commit()
                print("The existing local reference at " +
                      f"{git_user_repo_assoc.local_path_rel} with remote " +
                      f"{git_user_repo_assoc.remote_name} has been added to your current environment.")
            else:
                id = uuid.uuid4()
                git_user_repo_assoc = UserGitReposAssoc(id=id, user_id=user.id, repo_id=git_repo_entity.id,
                                                        remote_name=remote_name, local_path_rel=local_path)
                git_user_repo_assoc.client_envs.append(client_env_entity)
                git_repo_entity.userinfo.append(git_user_repo_assoc)
                db.session.add(git_repo_entity)
                db.session.commit()
            remote_name = git_user_repo_assoc.remote_name
            # a new reference has been created on the server for this environment, so client git config must be updated
            new_reference = True
        else:
            print("No new reference has been created. The existing local reference at " +
                  f"{git_user_repo_assoc_ref.local_path_rel} with remote " +
                  f"{git_user_repo_assoc_ref.remote_name} is already includes this remote repo.")
    gitrepo_schema = GitRepoFullSchema()
    response = gitrepo_schema.dump(git_repo_entity)
    response['remote_name'] = remote_name
    response['is_new_reference'] = new_reference
    # ToDo distinguish status codes: new created or already existing
    return response


def update_repo_for_clientenv(repo_id, client_env):
    from .model import GitRepo, UserGitReposAssoc, GitRepoFullSchema
    from ..model import User
    from ..decorators import requires_auth
    from ..database import db
    requires_auth()
    auth = request.authorization
    user = User.user_by_username(auth['username'])
    data = request.get_json(force=True)
    git_repo_entity = GitRepo.get_repo_by_id_and_user_id(repo_id, user.id)
    if not git_repo_entity:
        message = f"The repo {repo_id} does not exist for your user."
        raise InvalidRequest(message=message, field='repo_id', status_code=404)
    git_user_repo_assoc = find_git_user_repo_assoc(git_repo_entity, client_env)
    referenced_envs = [env.env_name for env in git_user_repo_assoc.client_envs]
    client_env_index = referenced_envs.index(client_env)
    if not git_user_repo_assoc:
        raise InvalidRequest(f"The repo is not referenced in the given environment {client_env}", 'client_env', 404)
    if 'server_path_rel' in data and data['server_path_rel']:
        if git_repo_entity.server_path_rel != data['server_path_rel']:
            fs_git_repo = GitRepoFs(git_repo_entity)
            success = fs_git_repo.move_repo(data['server_path_rel'])
            if success:
                git_repo_entity.server_path_rel = data['server_path_rel']
                db.session.add(git_repo_entity)
                db.session.commit()
    if 'local_path' in data and data['local_path']:
        if git_user_repo_assoc.local_path_rel != data['local_path']:
            if len(git_user_repo_assoc.client_envs) > 1:
                client_env_entity = git_user_repo_assoc.client_envs.pop(client_env_index)
                new_git_user_repo_assoc = find_git_user_repo_assoc_ref_by_local_path(git_repo_entity.userinfo,
                                                                                     data['local_path'])
                if not new_git_user_repo_assoc:
                    id = uuid.uuid4()
                    new_git_user_repo_assoc = UserGitReposAssoc(id=id, user_id=user.id, repo_id=git_repo_entity.id,
                                                                remote_name=git_user_repo_assoc.remote_name,
                                                                local_path_rel=data['local_path'])
                    new_git_user_repo_assoc.client_envs.append(client_env_entity)
                    db.session.add(new_git_user_repo_assoc)
            else:
                # Todo improve: delete git_user_repo_assoc if new local_path is already accommodated by another reference
                git_user_repo_assoc.local_path_rel = data['local_path']
            db.session.add(git_user_repo_assoc)
            db.session.commit()
        # else nothing changed
    user_gitrepo_schema = GitRepoFullSchema(many=False)
    return user_gitrepo_schema.dump(git_repo_entity)

def find_git_user_repo_assoc(git_repo_entity, client_env):
    # find the reference to git repo for this user
    git_user_repo_assoc = None
    for ind, user_info in enumerate(git_repo_entity.userinfo):
        referenced_envs = [env.env_name for env in user_info.client_envs]
        if client_env in referenced_envs:
            git_user_repo_assoc = user_info
            # existing reference found, abort lookup
            break
    return git_user_repo_assoc

def delete_repo(repo_id):
    from .model import GitRepo
    from ..model import User
    from ..decorators import requires_auth
    requires_auth()
    auth = request.authorization
    user = User.user_by_username(auth['username'])
    git_repo_entity = GitRepo.get_repo_by_id_and_user_id(repo_id, user.id)
    if not git_repo_entity:
        return
    git_repo_entity.remove()

def delete_repo_assoc_for_clientenv(repo_id, client_env):
    from .model import GitRepo
    from ..model import User
    from ..decorators import requires_auth
    requires_auth()
    auth = request.authorization
    user = User.user_by_username(auth['username'])
    git_repo_entity = GitRepo.get_repo_by_id_and_user_id(repo_id, user.id)
    if not git_repo_entity:
        message = f"The repo {repo_id} does not exist for your user."
        raise InvalidRequest(message=message, field='repo_id', status_code=404)
    git_user_repo_assoc = find_git_user_repo_assoc(git_repo_entity, client_env)
    if not git_user_repo_assoc:
        return
    git_user_repo_assoc.remove()

def find_git_user_repo_assoc_ref_by_local_path(user_infos, local_path):
    for user_info in user_infos:
        if user_info.local_path_rel == local_path:
            return user_info
    return None


def get_repos(full_info=False):
    from .model import UserGitReposAssoc, UserGitReposAssocSchema, UserGitReposAssocFullSchema
    user = get_user()
    if full_info:
        user_gitrepo_assoc_schema = UserGitReposAssocFullSchema(many=True)
    else:
        user_gitrepo_assoc_schema = UserGitReposAssocSchema(many=True)
    repos = UserGitReposAssoc.get_user_repos(_user_id=user.id)
    repo_list = dict()
    for client_env in user.client_envs:
        repo_list[client_env.env_name] = []
    if not repos:
        return jsonify(repo_list)
    for repo, client_env_name in repos:
        repo_list[client_env_name].append(repo)
    for client_env_name in repo_list:
        repo_list[client_env_name] = user_gitrepo_assoc_schema.dump(repo_list[client_env_name])
    return repo_list


def get_repos_by_clientenv(client_env, full_info=False):
    from .model import UserGitReposAssoc, UserGitReposAssocSchema, UserGitReposAssocFullSchema
    from ..model import ClientEnv
    user = get_user()
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


def get_user():
    from ..model import User
    from ..decorators import requires_auth
    requires_auth()
    auth = request.authorization
    return User.user_by_username(auth['username'])

# TODO: enrich class with logic 
class GitRepoUpdate:
    
    git_repo_dao = None
    
    def __init__(self, repo_id, user, GitRepo):
        self.user = user
        self.repo_id = repo_id
        self.git_repo = None
        __class__.git_repo_dao = GitRepo
    
    def load_repo(self):
        self.git_repo_entity = __class__.git_repo_dao.get_repo_by_id_and_user_id(self.repo_id, self.user.id) 
    
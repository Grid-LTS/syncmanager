# Syncmanager client

### Installation
#### Local development

##### 1. Install as local package
* this will provide you the syncmanager command
```
pip3 install -e .[dev] --user
```

##### 2. Install dependencies with Pipenv
* you need to have pipenv installed `pip3 install --user pipenv`
* run
```
pipenv install
pipenv shell
```

### Usage
All commands assume that you have installed the package locally with `pip install -e .[dev] --user`.

#### Synchronization with server
for pulling changes from the server
```
syncmanager pull [ -f $conf-file ]
```
for pushing to the server
```
syncmanager push [ -f $conf-file ]
```
#### Options
`-n, --namespace <ns>` : only sync folders under a certain names


#### Deletion of branches
Branches should not be deleted with `git branch -d <branch>` since they will be recreated on the next sync with the server.
Instead, use the syncmanager:
```
cd <your git repo>
syncmanager delete <branch name>
```

#### Setting configuration
for setting the config (name + email address only possible for git repos)
```
syncmanager set-conf
```

## Legacy client
binary: syncmanager-legacy
### configuration
- Git repositories have to be set up and wired by yourself for each client and the server
- *.conf-files: the path to the local Git project and the remote url of the server repo have to be provided in conf-files
- *.conf files should be in the home directory under ~/.sync-conf or can be provided as an argument to the call
- best would be to set up an easy authentification method with the server, like a key-based method, in order to avoid prompts when running the script
- for setting the git config for a repo, you need to provide the name + email address next to the repository path

### Requirements
Can only be run with python3 interpreter, e.g. MacOs or Linux distribution with git and unison installed (and a transfer protocol as ssh on client and server)

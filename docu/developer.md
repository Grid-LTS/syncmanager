# Developer space

## 1. Client

### Installation
1. install as package: see README.md
2. install dependencies in pipenv: see README.md

__Alternative:__  
with Virtualenv (deprecated)  
first install your platform's version of virtualenv  

run setup script  
`./setup.sh`  
running in virtual env  
`source venv/bin/activate`  

#### Add new packages
Append in `requirements.txt`  
run `pipenv install -r` for updating Pipfile

### Execution
Execute without installing: in case you want to run in from source, replace with:
```
cd <project root>/syncmanagerclient
python3 -m synchmanagerclient <arguments>
```

### Tests
Execute tests
```
cd <project-root>/syncmanagerclient
pipenv shell
python -m unittest tests/test_git_sync.py
```

## Server

### installation
* necessary both in DEV and PROD since both require MySQL database
```bash
deploy/install.sh
```

#### Known issues
pip installs packages like virtualenv, only if not existing. 
In case these packages are already installed, make sure they are up-to-date: 
```bash
# user specific installed
pip3 install --upgrade virtualenv --user
# system-wide
sudo pip3 install --upgrade virtualenv
```

* start in test mode
```
cd syncmanagerapi
python3 -m syncmanagerapi 
```
* create admin user (only possible via CLI)
on dev
```
cd syncmanagerapi
export FLASK_APP=syncmanagerapi 
flask admin-create --name <name> --password <password>
```
on prod:
```bash
sudo deploy/create_admin.sh
```
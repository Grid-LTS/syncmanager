# Developer space

## 1. Client (syncmanagerclient)

#### Installation
##### 1. Install as local package
* this will provide you the syncmanager command
```
python3 -m pip install -e .[dev] --user
```

##### 2. Install dependencies with Poetry
* you need to have poetry installed `pipx install poetry`
* run
```
poetry install
poetry shell
```

__Alternative:__  
with Virtualenv (deprecated)  
first install your platform's version of virtualenv  

run setup script  
`./setup.sh`  
running in virtual env  
`source venv/bin/activate`  

##### Add new packages
Append in `requirements.txt`  
run `poetry update` for updating dependencies

#### Execution
Execute without installing: in case you want to run in from source, replace with:
```
cd <project root>/syncmanagerclient
python3 -m synchmanagerclient <arguments>
```
##### 1. dev environment (SQLite db)
```bash
syncmanager --stage dev <command>
```



## 2. Server (syncmanagerapi)

### Installation
* on PROD, require MySQL database
```bash
deploy/install.sh
```
* local DEV environment (uses SQLite3 database)

```bash
# install SQLite3
sudo apt-get install sqlite3
windows: choco install sqlite
deploy/install_local.sh
```

```
sqlite3 syncmanagerapi.db
```

__Known issues__  
pip installs packages like virtualenv, only if not existing. 
In case these packages are already installed, make sure they are up-to-date: 
```bash
# user specific installed
pip3 install --upgrade virtualenv --user
# system-wide
sudo pip3 install --upgrade virtualenv
```

### Executing application
start in DEV mode

```
cd syncmanagerapi
python3 -m syncmanagerapi 
```

* verify server is available at http://localhost:8000/api/ui


create admin user (only possible via CLI)  
on DEV

```
cd syncmanagerapi
export FLASK_APP=syncmanagerapi 
$env:FLASK_APP="syncmanagerapi"
flask admin-create --name <name> --password <password>
```

on PROD:
```bash
sudo deploy/create_admin.sh
```


### Tests AND Continuous integration

#### api server
```
cd <project-root>/syncmanagerapi
poetry install
poetry shell
poetry up --only=dev --latest
pytest tests
```

#### client test and e2e test
e2e tests are part of the test collection for the syncmanagerclient modules
! you need to enable the virtual environment of the syncmanagerapi module because e2e tests require 
standalone api server to start
```
cd <project-root>/syncmanagerapi
poetry install
poetry shell
poetry up --only=dev --latest

cd <project-root>/syncmanagerclient 
pytest tests
```

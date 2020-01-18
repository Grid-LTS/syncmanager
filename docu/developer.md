# Developer space

### 1. Client (syncmanagerclient)

#### Installation
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

__Alternative:__  
with Virtualenv (deprecated)  
first install your platform's version of virtualenv  

run setup script  
`./setup.sh`  
running in virtual env  
`source venv/bin/activate`  

##### Add new packages
Append in `requirements.txt`  
run `pipenv install -r` for updating Pipfile

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



### 2. Server (syncmanagerapi)

#### Installation
* on PROD, require MySQL database
```bash
deploy/install.sh
```
* local DEV environment (uses SQLite3 database)
```bash
# install SQLite3
sudo apt-get install sqlite3 
deploy/install_local.sh
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

#### Executing application
start in DEV mode
```
cd syncmanagerapi
python3 -m syncmanagerapi 
```
create admin user (only possible via CLI)  
on DEV
```
cd syncmanagerapi
export FLASK_APP=syncmanagerapi 
flask admin-create --name <name> --password <password>
```
on PROD:
```bash
sudo deploy/create_admin.sh
```


### Tests
Execute tests
#### client (legacy)
```
cd <project-root>/syncmanagerclient
pipenv shell
python -m unittest tests/test_git_sync.py
python -m unittest tests/test_git_settings.py
```
#### api server
```
cd <project-root>/syncmanagerapi
pipenv shell
pytest tests
```
#### systemtest
to be done


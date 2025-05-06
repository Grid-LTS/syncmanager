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
* start in test mode
```
cd syncmanagerapi
python3 -m syncmanagerapi 
```
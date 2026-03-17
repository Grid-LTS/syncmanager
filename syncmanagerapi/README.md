


## Unstallation

* set up server unix
```
sudo usermod -aG myusers syncman
sudo chmod 775 <sync-dir>
sudo chmod g+s <sync-dir>
```

### Dependencies
###### Mysql or MariaDB:
  * Ubuntu:
    ```bash
    sudo apt-get -y install python3-dev default-libmysqlclient-dev libmysqlclient-dev
    # or  
    sudo apt install libmariadb-dev-compat 
    ```
    

## Local development
* apply database 
```
alembic upgrade heads
```

## Build
poetry build

## Local running instance
create application.<myorg>.cfg file similar to application.dev.cfg
1. create admin user
```
deploy/create_admin.sh
```
2. run server local
FLASK_ENV=<myorg> python -m syncmanagerapi

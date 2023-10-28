



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
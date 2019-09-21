#!/bin/bash

USER=$(whoami | awk '{print $1}')
SOURCE="${BASH_SOURCE[0]}"
SOURCE="$(readlink -f "$SOURCE")"
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd -P )"
PROJECT_DIR="$( dirname "$DIR" )"

PROPERTIES_FILE_NAME=application.prod.cfg

if [ -f "$PROJECT_DIR/$PROPERTIES_FILE_NAME" ]; then
  while IFS== read -r VAR1 VAR2
  do
    if [[ "$VAR1" == \#* || "$VAR2" == "" ]]; then
      continue
    fi
    if [ -n "$VAR2" ]; then
        VAR2="${VAR2//[\"\']}"
      export "$VAR1=${VAR2}"
    fi
  done < "$PROJECT_DIR/$PROPERTIES_FILE_NAME"
else
  echo "Create an ${PROPERTIES_FILE_NAME} file in the project root ${PROJECT_DIR}!"
  exit 1 
fi

if [ -z "$SERVER_PORT" ]; then
    echo "Property server_port not set"
    exit 1
fi

if [ -z "$UNIX_USER" ]; then
    echo "Property UNIX_USER not set"
    exit 1
fi
if [ -z "$INSTALL_DIR" ]; then
    echo "Property INSTALL_DIR not set"
    exit 1
fi

create_user() {
    UNIX_USER=$1
    echo "Create unix user ${UNIX_USER}."
    unix_password=$(openssl rand -base64 12)
    unix_password_encrypt=$(openssl passwd -crypt "$unix_password")
    USERS_SHELL=$(command -v rbash)
    if [ ! "$?" -eq 0 ]; then
        echo "Please install rbash on your system"
        exit 1
    fi
    sudo useradd -m --shell $USERS_SHELL -p "$unix_password_encrypt" $UNIX_USER
    if [ ! "$?" -eq 0 ]; then
        echo "Could not create user ${UNIX_USER}"
        exit 1
    else
        echo "The unix user has password: ${unix_password}"
    fi
    if [ ! -f /var/lib/AccountsService/users/$UNIX_USER ]; then
    cat <<- EOF | sudo tee /var/lib/AccountsService/users/$UNIX_USER
[User]
SystemAccount=true
EOF
    fi
    if [ ! -d /home/$UNIX_USER ]; then
        echo "The unix user ${UNIX_USER} has no home directory. Something went wrong."
        exit 1
    fi
    USER_BIN_DIR=/home/$UNIX_USER/usr/bin
    sudo mkdir -p $USER_BIN_DIR
    # Create profile
    sudo touch /home/$UNIX_USER/.bashrc
    echo "export PATH=/home/${UNIX_USER}/usr/bin" | sudo tee -a /home/$UNIX_USER/.bashrc
    for i in .bash_login .bash_profile .bash_logout .bash_profile .profile; 
    do 
        sudo cp /home/$UNIX_USER/.bashrc /home/$UNIX_USER/$i; 
    done
    UNISON_BIN=$(command -v unison)
    if [ "$?" -eq 0 ]; then
        sudo ln -s $UNISON_BIN $USER_BIN_DIR/unison
    else
        echo "Unison is not available on the server."
    fi
    sudo chmod -R 750 /home/$UNIX_USER
    sudo chown -R $UNIX_USER:$UNIX_USER /home/$UNIX_USER
}

# check if user exists
id -u $UNIX_USER >> /dev/null

if [ "$?" -ne 0 ]; then
    create_user $UNIX_USER
fi
# install system dependencies
sudo apt-get -y install libmysqlclient-dev


# build project
cd $PROJECT_DIR
rm -rf build
# remove old build artefacts
rm -rf dist
pip3 install --user pipenv
pipenv install
# in production we do need to set FLASK_ENV since the default is already 'production'

echo ""
pipenv run python setup.py bdist_wheel
VERSION=$(pipenv run python -c 'from properties import __version__; print(__version__)')
echo "Created project with version $VERSION"

package_name="${PROJECT_DIR}/dist/syncmanagerapi-${VERSION}-py3-none-any.whl"

command -v virtualenv > /dev/null
if [ ! "$?" -eq 0 ]; then
    pip3 install --upgrade virtualenv
    if [ "$?" -ne 0 ]; then
        python3 -m pip install --upgrade virtualenv
        if [ "$?" -ne 0 ]; then
            echo "Cannot install virtualenv package. Make sure you have pip3 installed."
            echo "Using the system package for pip is recommended, e.g. sudo apt-get install python3-pip"
            exit 1
        fi
    fi
fi

venv_dir=${INSTALL_DIR}/venv
sudo rm -r $venv_dir
sudo mkdir -p $venv_dir
sudo chown $USER:$USER $venv_dir
virtualenv -p $(which python3) $venv_dir
binaries=$venv_dir/bin
$binaries/pip install --upgrade gunicorn
$binaries/pip install $package_name

sudo chown root:root -R $venv_dir

# create systemd file
pipenv run python deploy/create_files.py syncmanagerapi.service

stty -echo
printf "MySQL password for admin user ${DB_ROOT_USER}: "
read db_password
stty echo

sudo mkdir $INSTALL_DIR/conf > /dev/null 2>&1
vars_file=$INSTALL_DIR/conf/application.cfg
if ! sudo mysql -h $DB_HOST -u $DB_ROOT_USER -P $DB_PORT -p$db_password -e "use ${DB_SCHEMA_NAME}" > /dev/null 2>&1; then
    echo "Initialize database for syncmanagerapi."
fi
    
query=$(sudo mysql -h $DB_HOST -u $DB_ROOT_USER -P $DB_PORT -p$db_password -e "SELECT 1 FROM mysql.user WHERE user = '${DB_USER}'")
echo "$query"    
if [ -n "$query" ]; then
    printf "MySQL user ${DB_USER} exists. Should the user be deleted?(Y, any other key for No)"
    read confirm
    
    if [ $confirm='Y' ] ||  [ $confirm='yes' ]; then
        sudo mysql -h $DB_HOST -u $DB_ROOT_USER -P $DB_PORT -p$db_password -e "DROP USER IF EXISTS ${DB_USER}"
    fi
fi
# read Mysql password of the DB_USER, so that it can be stored in properties file 
runtime_conf=$(pipenv run python deploy/create_files.py init_db.sql)

# Install database if does not exist
sudo mysql -h $DB_HOST -u $DB_ROOT_USER -h $DB_HOST -P $DB_PORT -p$db_password < deploy/init_db.sql
echo $runtime_conf | sudo tee $vars_file > /dev/null
# write out all other runtime variables
echo "DB_USER=\"${DB_USER}\"" | sudo tee -a $vars_file > /dev/null
echo "DB_SCHEMA_NAME=\"${DB_SCHEMA_NAME}\"" | sudo tee -a $vars_file > /dev/null
echo "DB_HOST=\"${DB_HOST}\""  | sudo tee -a $vars_file > /dev/null
echo "DB_PORT=${DB_PORT}"  | sudo tee -a $vars_file > /dev/null
echo "FS_ROOT=\"${FS_ROOT}\""    | sudo tee -a $vars_file > /dev/null
sudo chown -R $UNIX_USER:$UNIX_USER $INSTALL_DIR/conf
sudo chmod -R 700 $INSTALL_DIR/conf 
rm deploy/init_db.sql

# create root folder for file system
if [ ! -d $FS_ROOT ]; then
    sudo mkdir $FS_ROOT
    echo "Created directory ${FS_ROOT}."
fi

sudo mkdir $FS_ROOT/git 2>> /dev/null

sudo chown :$UNIX_USER -R $FS_ROOT
sudo chmod 770 -R $FS_ROOT

sudo mv deploy/syncmanagerapi.service /etc/systemd/system/
sudo systemctl enable syncmanagerapi
sudo systemctl status syncmanagerapi >> /dev/null
if [ "$?" -eq 0 ]; then
    sudo systemctl restart syncmanagerapi
else
    sudo systemctl start syncmanagerapi
fi
sudo systemctl status syncmanagerapi

sudo -E deploy/create_admin.sh

if [ -n "$unix_password" ]; then
    echo "The unix user has password $unix_password"
fi

echo "Cleanup dist/"
rm -rf dist
echo "Cleanup build/"
rm -rf build
#!/bin/bash

USER=$(whoami | awk '{print $1}')
SOURCE="${BASH_SOURCE[0]}"
SOURCE="$(readlink -f "$SOURCE")"
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd -P )"
PROJECT_DIR="$( dirname "$DIR" )"

if [ -f "$PROJECT_DIR/application.properties" ]; then
  echo "" >> "$PROJECT_DIR/application.properties"
  while IFS== read -r VAR1 VAR2
  do
    if [[ "$VAR1" == \#* || "$VAR2" == "" ]]; then
      continue
    fi
    if [ -n "$VAR2" ]; then
      export "$VAR1=$VAR2"
    fi
  done < "$PROJECT_DIR/application.properties"
else
  echo "Create an application.properties file in the project root ${PROJECT_DIR}!"
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
    if [ -z "$SHELL" ]; then
       SHELL=/bin/sh
    fi
    echo "Creating user with shell $SHELL"
    sudo useradd -M --shell $SHELL  -p '*' $UNIX_USER
    if [ ! -f /var/lib/AccountsService/users/$UNIX_USER ]; then
    cat <<- EOF | sudo tee /var/lib/AccountsService/users/$UNIX_USER
[User]
SystemAccount=true
EOF
    fi
    #echo "If necessary add the user ${UNIX_USER} to the privileged unix group for syncing 'sudo usermod -aG myusers ${UNIX_USER}'"
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

# remove old build artefacts
rm -r dist
pip3 install --user pipenv
pipenv install
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

sudo mv deploy/syncmanagerapi.service /etc/systemd/system/

stty -echo
printf "MySQL password for admin user ${DB_ROOT_USER}: "
read db_password
stty echo

sudo mkdir $INSTALL_DIR/conf > /dev/null 2>&1
vars_file=$INSTALL_DIR/conf/application.properties
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
echo "DB_USER=${DB_USER}" | sudo tee -a $vars_file > /dev/null
echo "DB_SCHEMA_NAME=${DB_SCHEMA_NAME}" | sudo tee -a $vars_file > /dev/null
echo "DB_HOST=${DB_HOST}"  | sudo tee -a $vars_file > /dev/null
echo "DB_PORT=${DB_PORT}"  | sudo tee -a $vars_file > /dev/null
echo "FS_ROOT=${FS_ROOT}" | sudo tee -a $vars_file > /dev/null
sudo chown -R $UNIX_USER:$UNIX_USER $INSTALL_DIR/conf
sudo chmod -R 700 $INSTALL_DIR/conf 
rm deploy/init_db.sql

# create root folder for file system
if [ ! -d $FS_ROOT ]; then
    sudo mkdir $FS_ROOT
    echo "Created directory ${FS_ROOT}."
fi
sudo mkdir $FS_ROOT/git
sudo chown :$UNIX_USER -R $FS_ROOT
sudo chmod 770 -R $FS_ROOT

echo "Do you want to create then initial administrative user? Leave prompt empty to skip."
read -p "Enter admin username: " admin_name

if [ -n "$admin_name" ]; then
    echo -n "Enter admin password: "
    read -s admin_pw
    
    source $INSTALL_DIR/venv/bin/activate
    export SYNCMANAGER_SERVER_CONF=$INSTALL_DIR/conf
    export FLASK_APP=syncmanagerapi
    flask admin-create --name $admin_name --password $admin_pw
    if [ "$?" -eq 0 ]; then
        echo "Created admin user ${admin_name}"
    fi
fi

sudo systemctl enable syncmanagerapi
sudo systemctl status syncmanagerapi >> /dev/null
if [ "$?" -eq 0 ]; then
    sudo systemctl restart syncmanagerapi
else
    sudo systemctl start syncmanagerapi
fi
sudo systemctl status syncmanagerapi
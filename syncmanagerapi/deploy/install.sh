#!/bin/bash

USER=$(who am i | awk '{print $1}')
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

if [ -z "$server_port" ]; then
    echo "Property server_port not set"
    exit 1
fi

if [ -z "$unix_user" ]; then
    echo "Property unix_user not set"
    exit 1
fi
if [ -z "$install_dir" ]; then
    echo "Property install_dir not set"
    exit 1
fi

create_user() {
    unix_user=$1
    echo "Create unix user ${unix_user}."
    if [ -z "$SHELL" ]; then
       SHELL=/bin/sh
    fi
    echo "Creating user with shell $SHELL"
    sudo useradd -M --shell $SHELL  -p '*' $unix_user
    if [ ! -f /var/lib/AccountsService/users/$unix_user ]; then
    cat <<- EOF | sudo tee /var/lib/AccountsService/users/$unix_user
    [User]
    SystemAccount=true
EOF
    fi
    echo "If necessarym add the user ${unix_user} to the privileged unix group for syncing 'sudo usermod -aG myusers ${unix_user}'"
}

# check if user exists
id -u $unix_user >> /dev/null

if [ "$?" -ne 0 ]; then
    create_user $unix_user
fi

# build project
cd $PROJECT_DIR

pip3 install --user pipenv
pipenv install
pipenv run python setup.py bdist_wheel
VERSION=$(pipenv run python -c 'from properties import __version__; print(__version__)')
echo "Created project with version $VERSION"

package_name="${PROJECT_DIR}/dist/syncmanagerapi-${VERSION}-py3-none-any.whl"

pip3 install --upgrade virtualenv
if [ "$?" -ne 0 ]; then
    python3 -m pip install --upgrade virtualenv    
fi
if [ "$?" -ne 0 ]; then
    echo "Cannot install virtualenv package. Make sure you have pip3 installed."
    echo "Using the system package for pip is recommended, e.g. sudo apt-get install python3-pip"
    exit 1 
fi

venv_dir=${install_dir}/venv
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
# Install database if does not exist
stty -echo
printf "MySQL password for user ${db_root_user}: "
read db_password
stty echo

sudo mkdir $install_dir/conf > /dev/null 2>&1
if ! sudo mysql -u $db_root_user -P $db_port -p$db_password -e "use ${db_schema_name}" > /dev/null 2>&1; then
    echo "Initialize database for syncmanagerapi."
    runtime_conf=$(exec pipenv run python deploy/create_files.py init_db.sql)
    sudo mysql -u $db_root_user -h $db_host -P $db_port -p$db_password < deploy/init_db.sql
    echo "db_user=${db_user}" | sudo tee $install_dir/conf/vars.conf > /dev/null
    echo $runtime_conf | sudo tee -a $install_dir/conf/vars.conf > /dev/null
    rm deploy/init_db.sql
fi

sudo systemctl enable syncmanagerapi
sudo systemctl status syncmanagerapi >> /dev/null
if [ "$?" -eq 0 ]; then
    sudo systemctl restart syncmanagerapi
else
    sudo systemctl start syncmanagerapi
fi
sudo systemctl status syncmanagerapi
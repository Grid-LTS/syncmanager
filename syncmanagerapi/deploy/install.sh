#!/bin/bash

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
    if [ -f /sbin/nologin ]; then
        NO_LOGIN_SHELL=/sbin/nologin
    elif [ -f /usr/sbin/nologin ]; then
        NO_LOGIN_SHELL=/usr/sbin/nologin
    else
        echo "Cannot find nologin shell"
        exit 1
    fi
    echo "no-login shell at $NO_LOGIN_SHELL"
    # this script has to be run as root
    sudo useradd -M --shell $NO_LOGIN_SHELL  -p '*' $unix_user
}

# check if user exists
id -u $unix_user

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
# create systemd file
pipenv run python deploy/create_files.py

package_name="${PROJECT_DIR}/dist/syncmanagerapi-${VERSION}-py3-none-any.whl"

sudo pip3 install --upgrade virtualenv
sudo virtualenv -p $(which python3) $install_dir
binaries=$install_dir/bin
sudo $binaries/pip install --upgrade gunicorn
sudo $binaries/pip install $package_name
sudo mv deploy/syncmanagerapi.service /etc/systemd/system/

sudo systemctl enable syncmanagerapi
sudo systemctl status syncmanagerapi
if [ "$?" -eq 0 ]; then
    sudo systemctl restart syncmanagerapi
else
    sudo systemctl start syncmanagerapi
fi
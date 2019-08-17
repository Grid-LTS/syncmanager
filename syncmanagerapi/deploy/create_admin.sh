#!/bin/bash

if [ -z "$INSTALL_DIR" ]; then
    echo "ENV variable $INSTALL_DIR not set."
    exit 1
fi

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
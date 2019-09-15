#!/bin/bash

USER=$(whoami | awk '{print $1}')
SOURCE="${BASH_SOURCE[0]}"
SOURCE="$(readlink -f "$SOURCE")"
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd -P )"
PROJECT_DIR="$( dirname "$DIR" )"

# assuming same environment for TEST and DEV
PROPERTIES_FILE_NAME=application.dev.properties

if [ -f "$PROJECT_DIR/$PROPERTIES_FILE_NAME" ]; then
  while IFS== read -r VAR1 VAR2
  do
    if [[ "$VAR1" == \#* || "$VAR2" == "" ]]; then
      continue
    fi
    if [ -n "$VAR2" ]; then
      export "$VAR1=$VAR2"
    fi
  done < "$PROJECT_DIR/$PROPERTIES_FILE_NAME"
else
  echo "Create an ${PROPERTIES_FILE_NAME} file in the project root ${PROJECT_DIR}!"
  exit 1 
fi

mkdir -p $PROJECT_DIR/$INSTALL_DIR/$FS_ROOT

#!/bin/bash

cd "$(dirname "$0")"
mv alembic.ini ..
cd ..
source $SYNCMANAGER_VENV_DIR/bin/activate
pip install pymysql
python alembic_cli.py
if [ "$?" -eq 0 ]; then
  rm alembic.ini
fi

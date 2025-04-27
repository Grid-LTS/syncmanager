#!/bin/bash

cd "$(dirname "$0")"
mv alembic.ini ..
cd ..
poetry run alembic upgrade head
if [ "$?" -eq 0 ]; then
  rm alembic.ini
fi

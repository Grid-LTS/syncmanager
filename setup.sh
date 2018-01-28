#!/bin/bash

if [ -z "$VIRTUAL_ENV" ]; then
    if [ ! -d venv ]; then
        python3 -m venv venv
    fi
     source venv/bin/activate
fi

pip install -U pip setuptools wheel
pip install -r requirements.txt
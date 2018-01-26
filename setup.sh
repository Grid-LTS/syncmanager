#!/bin/bash

if [ -z "$VIRTUAL_ENV" ]; then
    rm -r venv
    python3 -m venv venv
    source venv/bin/activate
fi

pip install -U pip setuptools wheel
pip install -r requirements.txt
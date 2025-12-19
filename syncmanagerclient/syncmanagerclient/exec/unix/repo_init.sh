#!/bin/bash
git config  core.fileMode false
find . -type f -name "._*" -delete
find . -type f -name ".DS_Store" -delete
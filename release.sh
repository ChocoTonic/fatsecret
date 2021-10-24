#!/usr/bin/env bash

# Simple script to automate the build and release of new packages. 
# This is based on the deployment guides found at
# https://packaging.python.org/tutorials/packaging-projects/

echo "> setting up build tools"
python3 -m pip install --upgrade build
python3 -m pip install --upgrade twine

echo "> creating new build"
python3 -m build

echo "> uploading build assets"
python3 -m twine upload --repository pypi dist/*
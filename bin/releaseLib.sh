#!/bin/bash

if [[ -z $1 ]]; then
    echo "Please specify the pypi user you are trying to use"
    exit 1
else
    PYPI_USER=$1
    echo "Using PYPI_USER $PYPI_USER"
fi

if [[ $PYPI_USER == *"prod"* ]]; then
    PYPI_LOCAL="perf-pypi-prod-local"
    ROLE="perf-pypi-prod"
else
    PYPI_LOCAL="perf-pypi-dev-local"
    ROLE="perf-pypi-dev"
fi

CURRENT_DIR=$(dirname "$0")
source $CURRENT_DIR/releaseFunctions.sh
echo "Using PYPI_LOCAL $PYPI_LOCAL"

setup-pypirc

python ${CURRENT_DIR}/../setup.py sdist

# upload the tar.gz distribution created under dist directory to Artifactory using Twine
pipenv run twine upload dist/* --repository ${PYPI_LOCAL}

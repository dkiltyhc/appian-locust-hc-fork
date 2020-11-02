#!/bin/bash
set -e
pipenv run pytest --cov-report term --cov=appian_locust tests/
pipenv run python -m pycodestyle appian_locust/*.py tests/*.py
pipenv run mypy --disallow-untyped-defs appian_locust/*.py tests/*.py

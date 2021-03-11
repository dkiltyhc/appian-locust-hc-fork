pipenv run pytest --cov-report term --cov-report html --cov=appian_locust tests/
pipenv run python -m pycodestyle appian_locust
pipenv run python -m pycodestyle tests
pipenv run mypy --disallow-untyped-defs appian_locust
pipenv run mypy --disallow-untyped-defs tests

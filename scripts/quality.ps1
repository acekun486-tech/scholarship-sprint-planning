$ErrorActionPreference = "Stop"

python -m ruff check .
python -m bandit -r app.py database.py -ll
python -m pytest -q --cov --cov-report=term-missing --cov-report=html --cov-fail-under=80
python -m coverage report --include="app.py" --fail-under=80
python -m coverage report --include="database.py" --fail-under=80
python -m radon cc app.py database.py -s -a --show-closures

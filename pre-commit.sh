python3 -m black src/ tests/
python3 -m isort --profile black src/ tests/
python3 -m flake8 src/ tests/ --max-line-length 88 --ignore E203,W503
python3 -m pyright src/ tests/

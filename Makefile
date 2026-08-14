.PHONY: test install bridge clean

test:
	.venv/bin/pytest -q

install:
	python3 -m venv .venv
	.venv/bin/pip install -q fastmcp pytest

bridge:
	.venv/bin/python src/dsh_bridge.py

clean:
	rm -rf task_board.json __pycache__ .pytest_cache

.PHONY: check test download-reference-data validate-reference smoke-test

check:
	python -m ruff check .
	python -m ruff format --check .
	python -m compileall -q src scripts tests
	bash -n hpc/helix/banksy_array.slurm hpc/helix/submit_banksy.sh

test: check
	python -m pytest -q

download-reference-data:
	python scripts/download_starmap_reference.py

validate-reference:
	python scripts/validate_starmap_reference.py

smoke-test: download-reference-data
	banksy-workflow check --config config/starmap_smoke.toml
	banksy-workflow run --config config/starmap_smoke.toml

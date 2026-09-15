.PHONY: check test download-reference-data validate-reference

check:
	python -m ruff check .
	python -m ruff format --check .
	bash -n hpc/banksy_array.slurm hpc/submit_banksy.sh

test: check
	python -m pytest -q

download-reference-data:
	python scripts/download_starmap_reference.py

validate-reference:
	python scripts/validate_starmap_reference.py

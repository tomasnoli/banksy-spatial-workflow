import pytest

from banksy_workflow.cli import build_parser, main

CONFIG = """
[data]
input = "{input}"
output = "results"
sample_name = "demo"

[parameters]
lambdas = [0.8]
resolutions = [0.2]
"""


def write_config(tmp_path, input_path):
    path = tmp_path / "config.toml"
    path.write_text(CONFIG.format(input=input_path.as_posix()))
    return path


def test_check_reports_missing_input(tmp_path):
    config = write_config(tmp_path, tmp_path / "missing.h5ad")
    with pytest.raises(SystemExit, match="Input file not found"):
        main(["check", "--config", str(config)])


def test_check_accepts_existing_input(tmp_path, capsys):
    input_path = tmp_path / "input.h5ad"
    input_path.write_bytes(b"")
    main(["check", "--config", str(write_config(tmp_path, input_path))])
    assert "Configuration valid" in capsys.readouterr().out


def test_run_accepts_standard_lambda_option():
    args = build_parser().parse_args(
        ["run", "--config", "analysis.toml", "--lambda", "0.8"]
    )
    assert args.lambda_values == [0.8]


def test_check_rejects_run_only_options():
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["check", "--config", "analysis.toml", "--sample", "sample_01"]
        )

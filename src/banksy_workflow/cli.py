from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="banksy-workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--config", type=Path, required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--config", type=Path, required=True)
    run_parser.add_argument("--sample", action="append")
    lambda_selection = run_parser.add_mutually_exclusive_group()
    lambda_selection.add_argument(
        "--lambda",
        dest="lambda_values",
        type=float,
        action="append",
        help="run one configured lambda value; repeat to select multiple values",
    )
    lambda_selection.add_argument("--lambda-index", type=int)
    run_parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    if args.command == "check":
        if not config.data.input.is_file():
            raise SystemExit(f"Input file not found: {config.data.input}")
        print(f"Configuration valid: {config.source}")
        print(f"Input: {config.data.input}")
        print(f"Output: {config.data.output}")
        return

    if args.lambda_index is not None:
        if args.lambda_index < 0:
            raise SystemExit("Lambda index must be zero or greater")
        try:
            requested_lambdas = [config.parameters.lambdas[args.lambda_index]]
        except IndexError as error:
            raise SystemExit(
                f"Lambda index {args.lambda_index} is outside the configured range"
            ) from error
    else:
        requested_lambdas = args.lambda_values
    from .core import run_workflow

    run_workflow(
        config,
        requested_samples=args.sample,
        requested_lambdas=requested_lambdas,
        force=args.force,
    )


if __name__ == "__main__":
    main()

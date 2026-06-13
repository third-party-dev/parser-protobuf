from __future__ import annotations

import argparse
from thirdparty.pparse.cli.registry import get_commands, load_entrypoint_plugins


def main() -> None:
    # Create parent parser
    parser = argparse.ArgumentParser(prog="pparse")
    
    parser.add_argument("--breakpoint",
        dest="breakpoint",
        action="store_true",
        help="breakpoint() after operation"
    )

    parser.add_argument("-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity"
    )

    parser.add_argument("--log-level",
        metavar="MODULE:LEVEL",
        action="append",
        default=[],
        help="Example: --log-level thirdparty.yannt:DEBUG"
    )

    subparsers = parser.add_subparsers(dest="pparse_command", required=True)

    # Load the entrypoints
    load_entrypoint_plugins("pparse_command")

    # Load plugins
    for registrar in get_commands():
        registrar(subparsers)

    args = parser.parse_args()

    args.func(args)
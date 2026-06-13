from __future__ import annotations

import logging
log = logging.getLogger(__name__)

from typing import Any

from thirdparty.pparse.cli.registry import get_commands, load_entrypoint_plugins


def register_pparse(subparsers: Any) -> None:
    pparse_parser = subparsers.add_parser("pparse", help="pparse command")
    
    pparse_parser.add_argument("--breakpoint",
        dest="breakpoint",
        action="store_true",
        help="breakpoint() after operation"
    )

    pparse_parser.add_argument("-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity"
    )

    pparse_parser.add_argument("--log-level",
        metavar="MODULE:LEVEL",
        action="append",
        default=[],
        help="Example: --log-level thirdparty.yannt:DEBUG"
    )

    pparse_subparser = pparse_parser.add_subparsers(dest="pparse_command", required=True)

    # Load the entrypoints
    load_entrypoint_plugins("pparse_command")

    # Load plugins
    for registrar in get_commands():
        registrar(pparse_subparser)


def run(args: Any) -> None:
    print("Running safetensors_parser command")
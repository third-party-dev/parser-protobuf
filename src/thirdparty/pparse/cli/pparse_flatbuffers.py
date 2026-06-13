from __future__ import annotations

import logging

log = logging.getLogger(__name__)

from typing import Any


def register_pparse_flatbuffers(subparsers: Any) -> None:
    flatbuffers_parser = subparsers.add_parser("flatbuffers", help="flatbuffers command")
    flatbuffers_subparser = flatbuffers_parser.add_subparsers(dest="flatbuffers_command", required=True)

    flatbuffers_view_parser = flatbuffers_subparser.add_parser("view", help="flatbuffers view command")
    flatbuffers_view_parser.add_argument("--print", action="store_true", help="print to stdout")
    flatbuffers_view_parser.add_argument("--offset", type=int, default=0)
    flatbuffers_view_parser.add_argument("json_schema_path")
    flatbuffers_view_parser.add_argument("path")
    flatbuffers_view_parser.set_defaults(func=flatbuffers_view)


def flatbuffers_view(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging

    activate_logging(args)

    from thirdparty.pparse.view.flatbuffers import Flatbuffers

    print(f"Parsing flatbuffers from: {args.path}")

    try:
        obj = Flatbuffers().open_fpath(args.path, json_schema_path=args.json_schema_path)
        root = obj._extraction._result['flatbuffers'].value

        if args.print:
            obj.root_node().dump()

    except Exception as e:
        print(e)
        import traceback

        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()

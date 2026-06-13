from __future__ import annotations

import logging
log = logging.getLogger(__name__)

from typing import Any


def register_pparse_json(subparsers: Any) -> None:
    json_parser = subparsers.add_parser("json", help="json command")
    json_subparser = json_parser.add_subparsers(dest="json_command", required=True)


    json_view_parser = json_subparser.add_parser("view", help="json view command")
    json_view_parser.add_argument("--print", action="store_true", help="print to stdout")
    json_view_parser.add_argument("path")
    json_view_parser.set_defaults(func=json_view)


def json_view(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.view.json import Json

    log.info(f"Parsing json from: {args.path}")

    try:
        obj = Json().open_fpath(args.path)
        root = obj._extraction._result['json']

        if args.print:
            obj.root_node().dump()

    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()



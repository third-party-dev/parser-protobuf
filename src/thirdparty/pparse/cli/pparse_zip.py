from __future__ import annotations

import logging
log = logging.getLogger(__name__)

from typing import Any


def register_pparse_zip(subparsers: Any) -> None:
    zip_parser = subparsers.add_parser("zip", help="zip command")
    zip_subparser = zip_parser.add_subparsers(dest="zip_command", required=True)


    zip_view_parser = zip_subparser.add_parser("view", help="zip view command")
    zip_view_parser.add_argument("--print", action="store_true", help="print to stdout")
    zip_view_parser.add_argument("path")
    zip_view_parser.set_defaults(func=zip_view)


def zip_view(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.view.zip import Zip

    print(f"Parsing zip from: {args.path}")

    try:
        obj = Zip().open_fpath(args.path)
        root = obj._extraction._result['zip']

        if args.print:
            obj.root_node().dump()

    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()



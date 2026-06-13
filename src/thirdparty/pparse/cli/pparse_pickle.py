from __future__ import annotations

import logging
log = logging.getLogger(__name__)

from typing import Any


def register_pparse_pickle(subparsers: Any) -> None:
    pickle_parser = subparsers.add_parser("pickle", help="pickle command")
    pickle_subparser = pickle_parser.add_subparsers(
        dest="pickle_command", required=True
    )

    pickle_parse_parser = pickle_subparser.add_parser(
        "view", help="pickle parse command"
    )
    pickle_parse_parser.add_argument("--print", action="store_true", help="print to stdout")
    pickle_parse_parser.add_argument("path")
    pickle_parse_parser.set_defaults(func=pickle_view)


def pickle_view(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.view.pickle import Pickle

    print(f"Parsing pickle from: {args.path}")

    try:
        obj = Pickle().open_fpath(args.path)
        pkl = obj.root_node()
        history = pkl.value[0].ctx().history

    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()

    if args.print:
        obj.root_node().dump()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()



from __future__ import annotations

import logging
log = logging.getLogger(__name__)

from typing import Any

def register_pparse_tflite(subparsers: Any) -> None:
    tflite_parser = subparsers.add_parser("tflite", help="tflite command")
    tflite_subparser = tflite_parser.add_subparsers(dest="tflite_command", required=True)


    tflite_view_parser = tflite_subparser.add_parser("view", help="tflite view command")
    tflite_view_parser.add_argument("--print", action="store_true", help="print to stdout")
    tflite_view_parser.add_argument("path")
    tflite_view_parser.set_defaults(func=tflite_view)


def tflite_view(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.view.tflite import TFLite

    print(f"Parsing tflite from: {args.path}")

    try:
        if args.path.startswith('http://') or args.path.startswith('https://'):
            obj = TFLite().open_url(args.path)
        else:
            obj = TFLite().open_fpath(args.path)
        tflite = obj._extraction._result['flatbuffers'].value

        if args.print:
            obj.root_node().dump()

    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()



from __future__ import annotations

import logging
log = logging.getLogger(__name__)

from typing import Any

def register_pparse_protobuf(subparsers: Any) -> None:
    protobuf_parser = subparsers.add_parser("protobuf", help="protobuf command")
    protobuf_subparser = protobuf_parser.add_subparsers(dest="protobuf_command", required=True)

    protobuf_view_parser = protobuf_subparser.add_parser("view", help="protobuf parse command")
    #protobuf_view_parser.add_argument("--dump", default=None)
    protobuf_view_parser.add_argument("--print", action="store_true", help="print to stdout")
    protobuf_view_parser.add_argument("pbpath")
    protobuf_view_parser.add_argument("msgtype")
    protobuf_view_parser.add_argument("path")
    protobuf_view_parser.set_defaults(func=protobuf_view)

def protobuf_view(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.view.protobuf import Parser as LazyProtobufParser

    print(f"Parsing protobuf from: {args.path}")

    try:
        obj = LazyProtobufParser().open_fpath(args.path, args.pbpath, args.msgtype)
        root = obj._extraction._result['protobuf']

        if args.print:
            obj.root_node().dump()

    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        print("Example:")
        print("  root.value['graph'].value['initializer'][4].value")
        print("Pattern:")
        print("  root.value[_field1_].value[_field2_].value[_field3_].value ...")
        breakpoint()




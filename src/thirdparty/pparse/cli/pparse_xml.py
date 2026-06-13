from __future__ import annotations

import logging
log = logging.getLogger(__name__)

from typing import Any


def register_pparse_xml(subparsers: Any) -> None:
    xml_parser = subparsers.add_parser("xml", help="xml command")
    xml_subparser = xml_parser.add_subparsers(dest="xml_command", required=True)

    xml_view_parser = xml_subparser.add_parser("view", help="xml view command")
    xml_view_parser.add_argument("--print", action="store_true", help="print to stdout")
    xml_view_parser.add_argument("path")
    xml_view_parser.set_defaults(func=xml_view)


def xml_view(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.view.xml import Xml

    print(f"Parsing xml from: {args.path}")

    try:
        obj = Xml().open_fpath(args.path)
        root = obj.root_node()
        et = obj.as_etree()

        if args.print:
            obj.root_node().dump()

    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()



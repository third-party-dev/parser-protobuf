from __future__ import annotations

import logging

log = logging.getLogger(__name__)

import traceback
from pprint import pprint
from typing import Any


def register_pparse_safetensors(subparsers: Any) -> None:
    safetensors_parser = subparsers.add_parser("safetensors", help="safetensors command")
    safetensors_subparser = safetensors_parser.add_subparsers(dest="safetensors_command", required=True)

    safetensors_view_parser = safetensors_subparser.add_parser("view", help="safetensors view command")
    safetensors_view_parser.add_argument("--print", action="store_true", help="print to stdout")
    safetensors_view_parser.add_argument("path")
    safetensors_view_parser.set_defaults(func=safetensors_view)

    safetensors_index_parser = safetensors_subparser.add_parser("index", help="safetensors index view command")
    safetensors_index_parser.add_argument("--print", action="store_true", help="print to stdout")
    safetensors_index_parser.add_argument("path")
    safetensors_index_parser.set_defaults(func=safetensors_index_view)

    safetensors_header_parser = safetensors_subparser.add_parser("header", help="safetensors header command")
    safetensors_header_parser.add_argument("path")
    safetensors_header_parser.set_defaults(func=raw_header)

    safetensors_pheader_parser = safetensors_subparser.add_parser("pheader", help="safetensors header command")
    safetensors_pheader_parser.add_argument("path")
    safetensors_pheader_parser.set_defaults(func=pparse_pheader)

    safetensors_hash_parser = safetensors_subparser.add_parser("hash", help="safetensors hash command")
    # debug argument
    safetensors_hash_parser.add_argument(
        "--hashed_data_path", dest="hashed_data_path", action="store", help="hashed data output", default=None
    )
    safetensors_hash_parser.add_argument("path")
    safetensors_hash_parser.set_defaults(func=safetensors_hash)


def safetensors_index_view(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging

    activate_logging(args)

    from thirdparty.pparse.view.safetensors import SafeTensorsIndex

    log.info(f"Viewing: {args.path}")

    obj = SafeTensorsIndex().open_fpath(args.path)

    if args.print:
        obj.root_node().dump()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()


def safetensors_view(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging

    activate_logging(args)

    from thirdparty.pparse.view.safetensors import SafeTensors

    log.info(f"Viewing: {args.path}")

    obj = SafeTensors().open_fpath(args.path)

    if args.print:
        obj.root_node().dump()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()


def raw_header(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging

    activate_logging(args)

    import json
    import struct

    log.info(f"Parsing header from: {args.path}")

    with open(args.path, "rb") as fobj:
        header_length = struct.unpack("<Q", fobj.read(8))[0]
        hdr_json = json.dumps(json.loads(fobj.read(header_length).decode()), indent=4)
        print(hdr_json)

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()


def pparse_pheader(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging

    activate_logging(args)

    from thirdparty.pparse.view.safetensors import SafeTensors

    # TODO: This needs some UX work.
    log.info(f"Parsing header from: {args.path}")

    obj = SafeTensors().open_fpath(args.path)
    pprint(obj.header())

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()


def safetensors_hash(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging

    activate_logging(args)

    from thirdparty.pparse.view.safetensors import SafeTensors

    log.info(f"Hashing safetensors from: {args.path} with: arc")

    try:
        obj = SafeTensors().open_fpath(args.path)
        print(obj.as_arc_hash(hashed_data_path=args.hashed_data_path))

    except Exception as e:
        print(e)
        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()

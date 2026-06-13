from __future__ import annotations

import logging

log = logging.getLogger(__name__)

from typing import Any


def register_pparse_onnx(subparsers: Any) -> None:
    onnx_parser = subparsers.add_parser("onnx", help="onnx command")
    onnx_subparser = onnx_parser.add_subparsers(dest="onnx_command", required=True)

    onnx_view_parser = onnx_subparser.add_parser("view", help="onnx parse command")
    onnx_view_parser.add_argument("--print", action="store_true", default=False, help="print to stdout")
    onnx_view_parser.add_argument("path")
    onnx_view_parser.set_defaults(func=onnx_view)

    # Generic "hash" command that implicitly does the "arc hash"
    onnx_hash_parser = onnx_subparser.add_parser("hash", help="onnx hash command")
    # debug argument
    onnx_hash_parser.add_argument(
        "--hashed_data_path",
        dest="hashed_data_path",
        action="store",
        help="hashed data output",
        default=None,
    )
    onnx_hash_parser.add_argument(
        "--keep_lm_head",
        dest="keep_lm_head",
        action="store_true",
        help="lm_head is removed without this flag",
        default=False,
    )
    onnx_hash_parser.add_argument("path")
    onnx_hash_parser.set_defaults(func=onnx_hash)

    # Generic "transform" command that implicitly does the "to safetensors" op
    onnx_transform_parser = onnx_subparser.add_parser("transform", help="transform pytorch")
    onnx_transform_parser.add_argument(
        "--keep_lm_head",
        dest="keep_lm_head",
        action="store_true",
        help="lm_head is removed without this flag",
        default=False,
    )
    onnx_transform_parser.add_argument("path")
    onnx_transform_parser.add_argument("outpath", default="converted_output.safetensors")
    onnx_transform_parser.set_defaults(func=onnx_transform)


def onnx_view(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging

    activate_logging(args)

    # from thirdparty.pparse.utils import pparse_repr
    from thirdparty.pparse.view.onnx import Onnx

    print(f"Parsing onnx from: {args.path}")

    try:
        obj = Onnx().open_fpath(args.path)
        root = obj._extraction._result['protobuf']
        # obj.tensor('lm_head.weight').get_data_bytes()

        if args.print:
            obj.root_node().dump()

    except Exception as e:
        print(e)
        import traceback

        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()


def onnx_hash(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging

    activate_logging(args)

    # from thirdparty.pparse.view.onnx import Onnx

    print(f"Hashing onnx from: {args.path} with: arc")

    # try:
    #     obj = Onnx().open_fpath(args.path)
    #     print(
    #         obj.as_arc_hash(
    #             hashed_data_path=args.hashed_data_path, keep_lm_head=args.keep_lm_head
    #         )
    #     )

    # except Exception as e:
    #     print(e)
    #     import traceback

    #     traceback.print_exc()

    # if hasattr(args, "breakpoint") and args.breakpoint:
    #     print(f"Locals: {list(locals().keys())}")
    #     breakpoint()


def onnx_transform(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging

    activate_logging(args)

    # from thirdparty.pparse.view.onnx import Onnx

    print(f"Transform pytorch from: {args.path} to: {args.outpath}")

    # try:
    #     obj = Onnx().open_fpath(args.path)
    #     obj.as_safetensors(args.outpath, keep_lm_head=args.keep_lm_head)

    # except Exception as e:
    #     print(e)
    #     import traceback

    #     traceback.print_exc()

    # if hasattr(args, "breakpoint") and args.breakpoint:
    #     print(f"Locals: {list(locals().keys())}")
    #     breakpoint()

from __future__ import annotations

import logging
log = logging.getLogger(__name__)

from typing import Any


def register_pparse_om(subparsers: Any) -> None:
    om_parser = subparsers.add_parser("om", help="om command")
    om_subparser = om_parser.add_subparsers(dest="om_command", required=True)

    om_header_parser = om_subparser.add_parser("header", help="om parse command")
    om_header_parser.add_argument("path")
    om_header_parser.set_defaults(func=om_header)

    om_parse_parser = om_subparser.add_parser("view", help="om view command")
    om_parse_parser.add_argument("--print", action="store_true", help="print to stdout")
    om_parse_parser.add_argument("path")
    om_parse_parser.set_defaults(func=om_parse)

    # om_view_parser = om_subparser.add_parser("view", help="om parse command")
    # om_view_parser.add_argument("path")
    # om_view_parser.set_defaults(func=om_view)

    # # Generic "hash" command that implicitly does the "arc hash"
    # om_hash_parser = om_subparser.add_parser("hash", help="om hash command")
    # # debug argument
    # om_hash_parser.add_argument(
    #     "--hashed_data_path",
    #     dest="hashed_data_path",
    #     action="store",
    #     help="hashed data output",
    #     default=None,
    # )
    # om_hash_parser.add_argument(
    #     "--keep_lm_head",
    #     dest="keep_lm_head",
    #     action="store_true",
    #     help="lm_head is removed without this flag",
    #     default=False,
    # )
    # om_hash_parser.add_argument("path")
    # om_hash_parser.set_defaults(func=om_hash)

    # # Generic "transform" command that implicitly does the "to safetensors" op
    # om_transform_parser = om_subparser.add_parser(
    #     "transform", help="transform pytorch"
    # )
    # om_transform_parser.add_argument(
    #     "--keep_lm_head",
    #     dest="keep_lm_head",
    #     action="store_true",
    #     help="lm_head is removed without this flag",
    #     default=False,
    # )
    # om_transform_parser.add_argument("path")
    # om_transform_parser.add_argument(
    #     "outpath", default="converted_output.safetensors"
    # )
    # om_transform_parser.set_defaults(func=om_transform)


def om_header(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.view.om import Om

    print(f"Parsing om header from: {args.path}")

    try:
        obj = Om().open_fpath(args.path, header_only=True)
        om = obj._extraction._result['om']
        print(om.dumps())

    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()


def om_parse(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    import thirdparty.pparse.lib as pparse
    from thirdparty.pparse.view.om import Om

    print(f"Parsing om header from: {args.path}")

    try:
        recursion = pparse.RecursionControl()
        obj = Om().open_fpath(args.path, recursion=recursion)
        #print(f"DEEPEST_DEPTH: {recursion.deepest_depth()}")

        #protobuf = obj.root_node()._value['partition_table']._value[1]._value['protobuf']._value

        if args.print:
            obj.root_node().dump()

        header = obj._extraction._result['om']
        #modeldef = obj._extraction._extractions[0]._result['protobuf']

    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        print("Example:")
        print("  print(header.dumps())")
        print("  print(modeldef.dumps())")
        breakpoint()

'''
from pprint import pprint
from thirdparty.pparse.view.om import Om
from thirdparty.pparse.utils import pparse_repr

om = Om().open_fpath('modeldef.pb')

# graph.op.input.attr.

graph = om._extraction._result['protobuf'].value['graph'].value[0]
with open('om.xml', 'w') as fobj:
    fobj.write(om._extraction._result['protobuf'].dumps())
first_packed = graph.value['op'].value[0].value['attr'].value[2].value['value'].value['list'].value['i'].value

desc = graph.value['op'].value[3].value['attr'].value[7].value['value'].value['t'].value['desc'].value
offset = desc['data_offset']
size = desc['weight_size']
dtype = desc['dtype']
shape = desc['shape'].value['dim'].value
'''



# def om_view(args):
#     from thirdparty.pparse.utils import pparse_repr
#     from thirdparty.pparse.view.om import Onnx

#     print(f"Parsing om from: {args.path}")

#     try:
#         obj = Onnx().open_fpath(args.path)
#         # obj.tensor('lm_head.weight').get_data_bytes()

#     except Exception as e:
#         print(e)
#         import traceback
#         traceback.print_exc()

#     if hasattr(args, "breakpoint") and args.breakpoint:
#         print(f"Locals: {list(locals().keys())}")
#         breakpoint()


# def om_hash(args):
#     from thirdparty.pparse.view.om import Onnx

#     print(f"Hashing om from: {args.path} with: arc")

#     # try:
#     #     obj = Onnx().open_fpath(args.path)
#     #     print(
#     #         obj.as_arc_hash(
#     #             hashed_data_path=args.hashed_data_path, keep_lm_head=args.keep_lm_head
#     #         )
#     #     )

#     # except Exception as e:
#     #     print(e)
#     #     import traceback

#     #     traceback.print_exc()

#     # if hasattr(args, "breakpoint") and args.breakpoint:
#     #     print(f"Locals: {list(locals().keys())}")
#     #     breakpoint()


# def om_transform(args):
#     from thirdparty.pparse.view.om import Onnx

#     print(f"Transform pytorch from: {args.path} to: {args.outpath}")

#     # try:
#     #     obj = Onnx().open_fpath(args.path)
#     #     obj.as_safetensors(args.outpath, keep_lm_head=args.keep_lm_head)

#     # except Exception as e:
#     #     print(e)
#     #     import traceback

#     #     traceback.print_exc()

#     # if hasattr(args, "breakpoint") and args.breakpoint:
#     #     print(f"Locals: {list(locals().keys())}")
#     #     breakpoint()

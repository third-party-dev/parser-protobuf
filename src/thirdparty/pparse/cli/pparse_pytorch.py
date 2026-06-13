from __future__ import annotations

import logging
log = logging.getLogger(__name__)

from typing import Any


def register_pparse_pytorch(subparsers: Any) -> None:
    pytorch_parser = subparsers.add_parser("pytorch", help="pytorch command")
    pytorch_subparser = pytorch_parser.add_subparsers(
        dest="pytorch_command", required=True
    )

    pytorch_view_parser = pytorch_subparser.add_parser(
        "view", help="pytorch parse command"
    )
    pytorch_view_parser.add_argument("--force_traverse", action="store_true", default=False)
    pytorch_view_parser.add_argument("--print", action="store_true", help="print to stdout")
    pytorch_view_parser.add_argument("path")
    pytorch_view_parser.set_defaults(func=pytorch_view)

    pytorch_unpickle_parser = pytorch_subparser.add_parser(
        "unpickle", help="pytorch unpickle command"
    )
    pytorch_unpickle_parser.add_argument("--print", action="store_true", help="print to stdout")
    pytorch_unpickle_parser.add_argument("path")
    pytorch_unpickle_parser.set_defaults(func=pytorch_unpickle)

    # Generic "hash" command that implicitly does the "arc hash"
    pytorch_hash_parser = pytorch_subparser.add_parser(
        "hash", help="pytorch hash command"
    )
    # debug argument
    pytorch_hash_parser.add_argument(
        "--hashed_data_path",
        dest="hashed_data_path",
        action="store",
        help="hashed data output",
        default=None,
    )
    pytorch_hash_parser.add_argument(
        "--keep_lm_head",
        dest="keep_lm_head",
        action="store_true",
        help="lm_head is removed without this flag",
        default=False,
    )
    pytorch_hash_parser.add_argument("path")
    pytorch_hash_parser.set_defaults(func=pytorch_hash)

    # Generic "transform" command that implicitly does the "to safetensors" op
    pytorch_transform_parser = pytorch_subparser.add_parser(
        "transform", help="transform pytorch"
    )
    pytorch_transform_parser.add_argument(
        "--keep_lm_head",
        dest="keep_lm_head",
        action="store_true",
        help="lm_head is removed without this flag",
        default=False,
    )
    pytorch_transform_parser.add_argument("path")
    pytorch_transform_parser.add_argument(
        "outpath", default="converted_output.safetensors"
    )
    pytorch_transform_parser.set_defaults(func=pytorch_transform)

    pytorch_nn_calls_parser = pytorch_subparser.add_parser(
        "nn-calls", help="list all torch.nn NewCalls found in the pickle"
    )
    pytorch_nn_calls_parser.add_argument("path")
    pytorch_nn_calls_parser.set_defaults(func=pytorch_nn_calls)


def pytorch_nn_calls(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)

    from thirdparty.pparse.view.pytorch import PyTorch
    from thirdparty.pparse.lazy.pytorch import iter_new_calls

    print(f"Parsing pytorch from: {args.path}")

    try:
        obj = PyTorch().open_fpath(args.path)
        pkl_root = obj.root_node()._value['pkl']
        for pkl_stream in pkl_root._value:
            for nc in iter_new_calls(pkl_stream._value):
                #if nc.module.startswith('torch.nn'):
                print(f"mod={nc.module}  func={nc.function}")
    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()


def pytorch_unpickle(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.view.pytorch import PyTorch

    print(f"Parsing pytorch from: {args.path}")

    try:
        obj = PyTorch().open_fpath(args.path)
        pkl = obj.root_node().value['pkl']
        # history = obj.root_node().value['pkl'].value[0].ctx().history

        if args.print:
            obj.root_node().value['pkl'].dump()

    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()


def pytorch_view(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    #from thirdparty.pparse.utils import pparse_repr
    from thirdparty.pparse.view.pytorch import PyTorch

    print(f"Parsing pytorch from: {args.path}")

    try:
        obj = PyTorch(force_traverse=args.force_traverse).open_fpath(args.path)
        # obj.tensor('lm_head.weight').get_data_bytes()
        pt = obj._extraction._result['pt']._value
        zip = obj._extraction._result['pt']._value['zip']._value

        if args.print:
            obj.root_node().dump()


    except Exception as e:
        print(e)
        import traceback

        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()

'''
    topcall = obj._extraction._extractions[0]._result['pkl'].value[0].value[0]
    metrics = { 'param_cnt': 0 }
    traverse(topcall.state, ['top'], metrics)
'''


def traverse(state: Any, path_arr: list[str], metrics: dict[str, int] = {'param_cnt': 0}) -> None:
    print(f"Traversing into {'.'.join(path_arr)} id: {id(state)}")

    if not isinstance(state, dict) or \
        not ('_modules' in state or '_parameters' in state):
        print("  - Dead end.")
        return

    if '_parameters' in state and len(state['_parameters'].keys()) > 0:
        print("  - Parameters found.")
        metrics['param_cnt'] += len(state['_parameters'].keys())


    if '_modules':
        for mod in state['_modules']:
            traverse(state['_modules'][mod].state, [*path_arr, mod], metrics)


def pytorch_hash(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.view.pytorch import PyTorch

    print(f"Hashing pytorch from: {args.path} with: arc")

    try:
        obj = PyTorch().open_fpath(args.path)
        print(
            obj.as_arc_hash(
                hashed_data_path=args.hashed_data_path, keep_lm_head=args.keep_lm_head
            )
        )

    except Exception as e:
        print(e)
        import traceback

        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        #traverse(obj._extraction._extractions[0]._result['pkl'].value[0].value[0], ['top'])
        breakpoint()


def pytorch_transform(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.view.pytorch import PyTorch

    print(f"Transform pytorch from: {args.path} to: {args.outpath}")

    try:
        obj = PyTorch().open_fpath(args.path)
        obj.as_safetensors(args.outpath, keep_lm_head=args.keep_lm_head)

    except Exception as e:
        print(e)
        import traceback

        traceback.print_exc()

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f"Locals: {list(locals().keys())}")
        breakpoint()

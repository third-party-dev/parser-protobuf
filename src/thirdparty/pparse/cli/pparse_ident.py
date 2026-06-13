from __future__ import annotations

import logging
log = logging.getLogger(__name__)

from typing import Any

def register_pparse_ident(subparsers: Any) -> None:
    ident_parser = subparsers.add_parser("ident", help="ident command")
    ident_subparser = ident_parser.add_subparsers(dest="ident_command", required=True)

    ident_list_parser = ident_subparser.add_parser("list", help="ident list command")
    ident_list_parser.set_defaults(func=ident_list)

    ident_show_parser = ident_subparser.add_parser("show", help="ident show command")
    ident_show_parser.add_argument("type_name")
    ident_show_parser.set_defaults(func=ident_show)

    ident_byext_parser = ident_subparser.add_parser("byext", help="ident list command")
    ident_byext_parser.add_argument("path")
    ident_byext_parser.set_defaults(func=ident_byext)


def ident_list(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.ident.extensions import typedb

    for k,val in typedb.items():
        print(f'{k} - {val["name"]}')

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f'Locals: {list(locals().keys())}')
        breakpoint()


def ident_show(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.ident.extensions import typedb

    if args.type_name not in typedb:
        print(f"No information on {args.type_name}. Please reference 'list' command.")
        exit(1)

    obj = typedb[args.type_name]
    print(f'Name: {obj["name"]}')
    print(f'Purpose: {obj["purpose"]}')
    print(f'Maintainer: {obj["maintainer"]}')
    if len(obj['links']) > 0:
        print(f'Links:')
        for link in obj['links']:
            print(f'- {link}')
    if len(obj['notes']) > 0:
        print(f'Notes:')
        for note in obj['notes']:
            print(f'- {note}')
    print(f'Extentions: {obj["exts"]}')

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f'Locals: {list(locals().keys())}')
        breakpoint()


def ident_byext(args: Any) -> None:
    from thirdparty.pparse.utils import activate_logging
    activate_logging(args)
    
    from thirdparty.pparse.ident.extensions import typedb, ident_by_extension

    print(f'Possible types: {ident_by_extension(args.path)}')

    if hasattr(args, "breakpoint") and args.breakpoint:
        print(f'Locals: {list(locals().keys())}')
        breakpoint()

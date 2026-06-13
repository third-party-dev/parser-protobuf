from __future__ import annotations

import io
import sys
import json
from typing import Any, Optional

from thirdparty.pparse.utils import ListType

'''
  The Dumper needs to be made more consistent with how it manages sampling truncation. At the
  moment, iterables can be annotated to be output as JSON. This is different than nodes that 
  are parsed as bytes where the data is only printed as a sample.

  Ideally we'd have a common CLI interface to represent what we want dumped.

  TODO: --dump-max-depth
  --print - A dump to STDOUT
  TODO: --dump-file - A dump to PATH
  TODO: --dump-max-array - A value of len() to use to determine when to snip arrays.
  TODO: --dump-max-string - A value of len() to use to determine when to snip arrays.
  TODO: --dump-json - Use a JSON dumper (lossy)

  Note: The above (except for --print) is prefixed with --dump to remain independent of the parsing
        arguments which may also include RecursionControl settings (--max-depth).
'''


def _print_cb(dst: Any = sys.stdout, value: str = '') -> None:
    try:
        print(value, file=dst)
    except BrokenPipeError:
        # Thrown when truncating output (e.g. head).
        return


class Dumper:
    MAX_DEPTH: int = 9223372036854775807
    _default: Optional[Dumper] = None


    @classmethod
    def default(cls) -> Dumper:
        if cls._default is None:
            cls._default = cls()
        return cls._default


    def __init__(self, dumpers: Optional[list[Any]] = None, cb: Any = _print_cb, dst: Any = sys.stdout, max_array: int = MAX_DEPTH, max_depth: int = MAX_DEPTH) -> None:
        import numbers
        from thirdparty.pparse.lib import Node
        from collections.abc import Iterable

        self.max_array: int = max_array
        if self.max_array < 4:
            # Less than 4 over complicates the snip output.
            self.max_array = 4

        self.max_depth: int = max_depth

        self.dumpers: list[Any] = dumpers
        if self.dumpers is None:
            self.dumpers = [
                [Node, self._dump_node_wrapper],
                [dict, self._dump_dict_wrapper],
                [bytes, self._dump_bytes_wrapper],
                [str, self._dump_str_wrapper],
                [int, self._dump_misc_wrapper],
                [float, self._dump_misc_wrapper],
                [numbers.Number, self._dump_misc_wrapper],
                [bool, self._dump_misc_wrapper],
                [type(None), self._dump_misc_wrapper],
                [io.BytesIO, self._dump_bytesio_wrapper],
                [Iterable, self._dump_iter_wrapper],
            ]
        
        self.cb=cb
        self.dst=dst


    def _dump_node_wrapper(self, elem_name: str = "entry", obj: Any = None, attrs: str = '', depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        spacer = " " * depth
        self.cb(self.dst, f'{spacer}<{elem_name} value_is="Node" {attrs}>')
        obj.dump(depth + step)
        closing_attrs = ''
        if attrs and len(attrs) > 0:
            closing_attrs = f'<!-- tag_attrs: {attrs} -->'
        self.cb(self.dst, f'{spacer}</{elem_name}>{closing_attrs}')


    def _dump_dict_wrapper(self, elem_name: str = "entry", obj: Any = None, attrs: str = '', depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        spacer = " " * depth
        if len(obj.keys()) == 0:
            self.cb(self.dst, f'{spacer}<{elem_name} value_is="dict" {attrs} empty="y"></{elem_name}>')
        else:
            self.cb(self.dst, f'{spacer}<{elem_name} value_is="dict" {attrs}>')
            self._dump_dict(obj, depth + step)
            closing_attrs = ''
            if attrs and len(attrs) > 0:
                closing_attrs = f'<!-- tag_attrs: {attrs} -->'
            self.cb(self.dst, f'{spacer}</{elem_name}>{closing_attrs}')


    def _dump_bytes_wrapper(self, elem_name: str = "entry", obj: Any = None, attrs: str = '', depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        spacer = " " * depth
        if len(obj) == 0:
            self.cb(self.dst, f'{spacer}<{elem_name} value_is="bytes" {attrs} empty="y"></{elem_name}>')
        else:
            self.cb(self.dst, f'{spacer}<{elem_name} value_is="bytes" {attrs} length="{len(obj)}">')
            self._dump_bytes(obj, depth + step)
            closing_attrs = ''
            if attrs and len(attrs) > 0:
                closing_attrs = f'<!-- tag_attrs: {attrs} -->'
            self.cb(self.dst, f'{spacer}</{elem_name}>{closing_attrs}')


    def _dump_str_wrapper(self, elem_name: str = "entry", obj: Any = None, attrs: str = '', depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        spacer = " " * depth
        if len(obj) == 0:
            self.cb(self.dst, f'{spacer}<{elem_name} value_is="str" {attrs} empty="y"></{elem_name}>')
        else:
            self.cb(self.dst, f'{spacer}<{elem_name} value_is="str" {attrs} length="{len(obj)}">')
            self._dump_str(obj, depth + step)
            closing_attrs = ''
            if attrs and len(attrs) > 0:
                closing_attrs = f'<!-- tag_attrs: {attrs} -->'
            self.cb(self.dst, f'{spacer}</{elem_name}>{closing_attrs}')


    def _dump_misc_wrapper(self, elem_name: str = "entry", obj: Any = None, attrs: str = '', depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        spacer = " " * depth
        self.cb(self.dst, f'{spacer}<{elem_name} value_is="scalar" {attrs}>{obj}</{elem_name}>')


    def _dump_bytesio_wrapper(self, elem_name: str = "entry", obj: Any = None, attrs: str = '', depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        spacer = " " * depth
        self.cb(self.dst, f'{spacer}<{elem_name} value_is="BytesIO" {attrs}>{obj}</{elem_name}>')


    def _dump_iter_wrapper(self, elem_name: str = "entry", obj: Any = None, attrs: str = '', depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        spacer = " " * depth
        if len(obj) == 0:
            self.cb(self.dst, f'{spacer}<{elem_name} value_is="list" {attrs} empty="y"></{elem_name}>')

        elif hasattr(obj, "_pparse_type") and obj._pparse_type != ListType.MIXED:

            if obj._pparse_type == ListType.INT:
                attrs = f'{attrs} type="int" count="{len(obj)}"'
                self.cb(self.dst, f'{spacer}<{elem_name} value_is="list" encoding="json" {attrs}>')
                self.cb(self.dst, f'{spacer}{" " * step}{json.dumps(obj)}')
                closing_attrs = ''
                if attrs and len(attrs) > 0:
                    closing_attrs = f'<!-- tag_attrs: {attrs} -->'
                self.cb(self.dst, f'{spacer}</{elem_name}>{closing_attrs}')
                return

            if obj._pparse_type == ListType.FLOAT:
                attrs = f'{attrs} type="float" count="{len(obj)}"'
                self.cb(self.dst, f'{spacer}<{elem_name} value_is="list" encoding="json" {attrs}>')
                ## TODO: I don't like this. I'd rather use hex values, but that isn't JSON compliant. :(
                #for i in range(0, len(obj), 3):
                #    chunk = obj[i:i+3]
                #    # Note: fp64 - 17, fp32 - 9, fp16 - 6
                #    line = ' '.join(f'{n:20.9g}{"," if i + j < len(obj) - 1 else ""}' for j, n in enumerate(chunk))
                #    #line = ''.join(f'{n:3d}, ' for n in obj[i:i+16])
                #    self.cb(self.dst, f'{spacer}{line}')
                self.cb(self.dst, f'{spacer}{" " * step}{json.dumps(obj)}')
                closing_attrs = ''
                if attrs and len(attrs) > 0:
                    closing_attrs = f'<!-- tag_attrs: {attrs} -->'
                self.cb(self.dst, f'{spacer}</{elem_name}>{closing_attrs}')
                return
            if obj._pparse_type == ListType.UBYTE:
                attrs = f'{attrs} type="ubyte" count="{len(obj)}"'
                self.cb(self.dst, f'{spacer}<{elem_name} value_is="list" encoding="json" {attrs}>')
                self.cb(self.dst, f'{spacer}{" " * step}{json.dumps(obj)}')
                closing_attrs = ''
                if attrs and len(attrs) > 0:
                    closing_attrs = f'<!-- tag_attrs: {attrs} -->'
                self.cb(self.dst, f'{spacer}</{elem_name}>{closing_attrs}')
                return

            if obj._pparse_type == ListType.BYTE:
                attrs = f'{attrs} type="byte" count="{len(obj)}"'
                self.cb(self.dst, f'{spacer}<{elem_name} value_is="list" encoding="json" {attrs}>')
                #for i in range(0, len(obj), 16):
                #    chunk = obj[i:i+16]
                #    line = ' '.join(f'{n:3d}{"," if i + j < len(obj) - 1 else ""}' for j, n in enumerate(chunk))
                #    #line = ''.join(f'{n:3d}, ' for n in obj[i:i+16])
                #    self.cb(self.dst, f'{spacer}{line}')
                self.cb(self.dst, f'{spacer}{" " * step}{json.dumps(obj)}')
                closing_attrs = ''
                if attrs and len(attrs) > 0:
                    closing_attrs = f'<!-- tag_attrs: {attrs} -->'
                self.cb(self.dst, f'{spacer}</{elem_name}>{closing_attrs}')
                return

        # Fall through catch all.
        self.cb(self.dst, f'{spacer}<{elem_name} value_is="list" {attrs}>')
        self._dump_list(obj, depth + step)
        closing_attrs = ''
        if attrs and len(attrs) > 0:
            closing_attrs = f'<!-- tag_attrs: {attrs} -->'
        self.cb(self.dst, f'{spacer}</{elem_name}>{closing_attrs}')


    def _dump_else_wrapper(self, elem_name: str = "entry", obj: Any = None, attrs: str = '', depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        spacer = " " * depth
        self.cb(self.dst, f'{spacer}<{elem_name} value_is="unknown" {attrs}>')
        self.cb(self.dst, f'{spacer}{obj}')
        closing_attrs = ''
        if attrs and len(attrs) > 0:
            closing_attrs = f'<!-- tag_attrs: {attrs} -->'
        self.cb(self.dst, f'{spacer}</{elem_name}>{closing_attrs}')


    def _dump_str(self, obj: Any, depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        spacer = " " * depth
        self.cb(self.dst, f'{spacer}<string>{obj}</string>')


    def _dump_bytes(self, obj: Any, depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        # Bytes can be expressed in many ways:
        # hex dump, byte string dump, byte hex string dump, snippets.

        # As a default, we'll dump as is for first 16 bytes. If larger than
        # 16 bytes, we'll print the first 16 bytes and last 16 bytes.

        spacer = " " * depth
        if len(obj) <= 16:
            self.cb(self.dst, f'{spacer}{obj}')
        elif len(obj) >16:
            self.cb(self.dst, f'{spacer}{obj[:16]}')
            if len(obj) >= 32:
                self.cb(self.dst, f'{spacer}... snip ...')
                self.cb(self.dst, f'{spacer}{obj[-16:]}')
            else:
                self.cb(self.dst, f'{spacer}{obj[16:]}')


    # from thirdparty.pparse.lib import Node
    # print(ppobj.root_node().dump())
    def _dump_list(self, obj: Any, depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        for idx in range(len(obj)):
            entry = obj[idx]
            entry_attrs = [f'idx="{idx}"']
            self.dump("entry", entry, ' '.join(entry_attrs), depth=depth, step=step)


    def _dump_dict(self, obj: Any, depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        for key in obj:
            entry = obj[key]
            entry_attrs = [f'key="{key}"']
            self.dump("entry", entry, ' '.join(entry_attrs), depth=depth, step=step)


    # ** The only public call. **
    def dump(self, elem_name: str = "entry", obj: Any = None, attrs: str = '', depth: int = 0, step: int = 2) -> None:
        if depth > self.max_depth:
            return

        for dumper in self.dumpers:
            if isinstance(obj, dumper[0]):
                dumper[1](elem_name=elem_name, obj=obj, attrs=attrs, depth=depth, step=step)
                return
        self._dump_else_wrapper(elem_name=elem_name, obj=obj, attrs=attrs, depth=depth, step=step)



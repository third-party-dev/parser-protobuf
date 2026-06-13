#!/usr/bin/env python3

from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger(__name__)

# from thirdparty.pparse.lazy.protobuf import ProtobufParsingState, ProtobufParsingKey
import io
import sys
import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.pickle.calls import ReduceCall, PersistentCall, NewCall
from thirdparty.pparse.dump import Dumper, _print_cb


class NodeVmContext(pparse.NodeContext):
    def __init__(self, parent: Optional[pparse.Node], reader: pparse.Range, parser: pparse.Parser) -> None:
        if type(reader).__name__ != "Range":
            raise Exception("protobuf NodeContext reader must be a pparse.Range")
        super().__init__(parent, reader, parser)

        self.proto: Any = None
        self.current_op: Any = None
        self.stack: list[Any] = []
        self.memo: dict[int, Any] = {}
        self.next_memo: int = 0

        # Note: Save the history to the node, forever allocating that memory.
        self.history: list[Any] = []

    def vmstate(self) -> Any:
        return self._vmstate


class Node(pparse.Node):
    def dump(self, depth: int = 0, step: int = 2, dumper: Optional[PickleDumper] = None) -> None:
        if not dumper:
            dumper = PickleDumper()
        # TODO: Consider the ReduceCall dict AND _value.
        dumper.dump("Node", self._value, '', depth=depth, step=step)


class PickleDumper(Dumper):
    def __init__(self, dumpers: Optional[list[Any]] = None, cb: Any = _print_cb, dst: Any = sys.stdout) -> None:
        import numbers
        from thirdparty.pparse.lib import Node
        from collections.abc import Iterable

        self.dumpers = dumpers
        if self.dumpers is None:
            self.dumpers = [
                [NewCall, self._dump_newcall_wrapper],
                [ReduceCall, self._dump_reducecall_wrapper],
                [PersistentCall, self._dump_persidcall_wrapper],
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
        super().__init__(dumpers=self.dumpers, cb=cb, dst=dst)


    def _dump_newcall_wrapper(self, elem_name: str = "NewCall", obj: Any = None, attrs: str = '', depth: int = 0, step: int = 2) -> None:
        spacer = " " * depth
        attrs = ' '.join([
            f'mod="{obj.module_call[0].decode("utf-8").strip()}"',
            f'func="{obj.module_call[1].decode("utf-8").strip()}"',
        ])
        self.cb(self.dst, f'{spacer}<NewCall {attrs}>')
        
        if obj.arg is None or len(obj.arg) == 0:
            self.cb(self.dst, f'{spacer}{" " * step}<args is_empty="y" />')
        else:
            self.cb(self.dst, f'{spacer}{" " * step}<args count="{len(obj.arg)}">')
            self._dump_list(obj.arg, depth + (step * 2))
            self.cb(self.dst, f'{spacer}{" " * step}</args>')

        if obj.state is None:
            self.cb(self.dst, f'{spacer}{" " * step}<state is_empty="y" />')
        else:
            self.cb(self.dst, f'{spacer}{" " * step}<state key_count="{len(obj.state)}">')
            self._dump_dict(obj.state, depth + (step * 2))
            self.cb(self.dst, f'{spacer}{" " * step}</state>')

        if len(obj) == 0:
            self.cb(self.dst, f'{spacer}{" " * step}<dict is_empty="y">')
        else:
            self.cb(self.dst, f'{spacer}{" " * step}<dict key_count="{len(dict(obj))}">')
            self._dump_dict(dict(obj), depth + (step * 2))
            self.cb(self.dst, f'{spacer}{" " * step}</dict>')

        self.cb(self.dst, f'{spacer}</NewCall>')


    def _dump_reducecall_wrapper(self, elem_name: str = "ReduceCall", obj: Any = None, attrs: str = '', depth: int = 0, step: int = 2) -> None:
        spacer = " " * depth
        attrs = ' '.join([
            f'mod="{obj.module_call[0].decode("utf-8").strip()}"',
            f'func="{obj.module_call[1].decode("utf-8").strip()}"',
        ])
        self.cb(self.dst, f'{spacer}<ReduceCall {attrs}>')
        
        if obj.arg is None or len(obj.arg) == 0:
            self.cb(self.dst, f'{spacer}{" " * step}<args is_empty="y" />')
        else:
            self.cb(self.dst, f'{spacer}{" " * step}<args count="{len(obj.arg)}">')
            self._dump_list(obj.arg, depth + (step * 2))
            self.cb(self.dst, f'{spacer}{" " * step}</args>')

        if obj.state is None:
            self.cb(self.dst, f'{spacer}{" " * step}<state is_empty="y" />')
        else:
            self.cb(self.dst, f'{spacer}{" " * step}<state key_count="{len(obj.state)}">')
            self._dump_dict(obj.state, depth + (step * 2))
            self.cb(self.dst, f'{spacer}{" " * step}</state>')

        if len(dict(obj)) == 0:
            self.cb(self.dst, f'{spacer}{" " * step}<dict is_empty="y" />')
        else:
            self.cb(self.dst, f'{spacer}{" " * step}<dict key_count="{len(dict(obj))}">')
            self._dump_dict(dict(obj), depth + (step * 2))
            self.cb(self.dst, f'{spacer}{" " * step}</dict>')

        self.cb(self.dst, f'{spacer}</ReduceCall>')
    
    def _dump_persidcall_wrapper(self, elem_name: str = "PersistentCall", obj: Any = None, attrs: str = '', depth: int = 0, step: int = 2) -> None:
        spacer = " " * depth
        attrs = ' '.join([
            f'id="{obj.id}"',
        ])
        self.cb(self.dst, f'{spacer}<PersistentCall {attrs}>')
        
        self.cb(self.dst, f'{spacer}{" " * step}<args>')
        #self.cb(self.dst, f'{spacer}{" " * step}{obj.arg}')
        self._dump_list(obj.arg, depth + (step * 2))
        self.cb(self.dst, f'{spacer}{" " * step}</args>')

        self.cb(self.dst, f'{spacer}</PersistentCall>')

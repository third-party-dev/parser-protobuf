#!/usr/bin/env python3

from __future__ import annotations

import logging
import struct
from typing import Any, Optional, Type

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.protobuf.meta import Protobuf, PbImport
from thirdparty.pparse.lazy.protobuf.node import NodeContext
from thirdparty.pparse.lazy.protobuf.state import ProtobufParsingTag, ProtobufParsingState


def configure_pparser(**kwargs: Any) -> Type[pparse.Parser]:

    ext_list = []
    if 'ext_list' in kwargs:
        ext_list = kwargs['ext_list']

    init_msgtype = ""
    if 'init_msgtype' in kwargs:
        init_msgtype = kwargs['init_msgtype']

    #pkg_namespace = None
    #relative_path = None
    proto = PbImport()
    if 'pkg_namespace' in kwargs and 'relative_path' in kwargs:
        from importlib import resources
        data_path = resources.files(kwargs['pkg_namespace'])
        proto = PbImport(data_path / kwargs['relative_path'])
        #proto = kwargs['proto']

    class Parser(pparse.Parser):


        @staticmethod
        def match_extension(fname: str) -> bool:
            if not fname:
                return False
            # for ext in ['.onnx']:
            for ext in ext_list:
                if fname.endswith(ext):
                    return True
            return False


        @staticmethod
        def match_magic(cursor: pparse.Cursor) -> bool:
            return False


        @staticmethod
        def from_reader(reader: pparse.Reader, parent: Optional[pparse.Node] = None) -> pparse.Parser:
            extraction = pparse.BytesExtraction(name="data.pb", reader=reader.dup())
            return Parser(extraction, parent=parent)


        def make_root_node(self, parent: Optional[pparse.Node] = None, init_state: Type[ProtobufParsingState] = ProtobufParsingTag) -> pparse.Node:
            init_state = self._init_state_as_cls(init_state)

            root = pparse.Node(self._source.open(), self, default_value={}, parent=parent, ctx_class=NodeContext)
            root.ctx()._next_state(init_state)
            root.ctx()._type_desc = self.schema.by_type_name(init_msgtype)

            return root


        def __init__(self, source: pparse.Extraction, id: str = "protobuf") -> None:
            super().__init__(source, id, ProtobufParsingState)

            self.schema = proto

            # Initial node is a map of type '.onnx.ModelProto'
            # protobuf_type = proto.by_type_name('.onnx.ModelProto')
            #protobuf_type = self.schema.by_type_name(init_msgtype)

            # TODO: Consider adding hook for booking as the nodes are completed.
            # # def _node_complete_callable(parser, node_ctx, user_arg):
            # self._node_complete_callable = None
            # self._node_complete_arg = None


        def _parse_varint(self, ctx: pparse.NodeContext, peek: bool = False) -> tuple[int, int]:
            value = 0
            shift = 0
            start = ctx.tell()

            while True:
                u8 = ctx.read(1)
                if not u8 or len(u8) < 1:
                    msg = f"Not enough data to parse Protobuf varint. Offset: {ctx.tell()}"
                    raise pparse.EndOfDataException(msg)
                u8 = ord(u8)
                value |= (u8 & 0x7F) << shift
                if not (u8 & 0x80):
                    break
                shift += 7

            end = ctx.tell()
            if peek:
                ctx.seek(start)
            return value, end - start


        def parse_varint(self, ctx: pparse.NodeContext) -> int:
            return self._parse_varint(ctx, False)[0]


        def peek_varint(self, ctx: pparse.NodeContext) -> tuple[int, int]:
            return self._parse_varint(ctx, True)


        def peek_varint_key(self, ctx: pparse.NodeContext) -> tuple[int, int, int, Optional[int]]:
            # Note: Key varints (by spec) ar always 32 bits (fields are 29 bits)
            current_pos = ctx.tell()
            value, key_length = self._parse_varint(ctx)
            wire_type = value & 0x7
            field_num = value >> 3
            value_length = None
            value_length_length = 0
            if wire_type == Protobuf.LEN:
                value_length, value_length_length = self._parse_varint(ctx)
            meta_length = key_length + value_length_length

            ctx.seek(current_pos)

            return wire_type, field_num, meta_length, value_length


        def parse_varint_key(self, ctx: pparse.NodeContext) -> tuple[int, int]:
            value = self.parse_varint(ctx)
            return (value & 0x7), (value >> 3)


        def parse_i32(self, ctx: pparse.NodeContext, peek: bool = False) -> int:
            data = None
            if peek:
                data = ctx.peek(4)
            else:
                data = ctx.read(4)
            if not data or len(data) < 4:
                msg = (
                    f"Not enough data to parse Protobuf I32 data. Offset: {ctx.tell()}"
                )
                raise pparse.EndOfDataException(msg)
            return struct.unpack("<I", data)[0]


        def parse_i64(self, ctx: pparse.NodeContext, peek: bool = False) -> int:
            data = None
            if peek:
                data = ctx.peek(8)
            else:
                data = ctx.read(8)
            if not data or len(data) < 8:
                msg = (
                    f"Not enough data to parse Protobuf I64 data. Offset: {ctx.tell()}"
                )
                raise pparse.EndOfDataException(msg)
            return struct.unpack("<Q", data)[0]


        # def _apply_value(self, ctx: pparse.NodeContext, field: Any, value: Any) -> None:
        #     if isinstance(self.current, NodeArray):
        #         log.debug(
        #             f"apply_value (off:{ctx.tell()}): Inside {self.current}. Append value."
        #         )
        #         self.current.value.append(value)
        #         return
        #     elif isinstance(self.current, NodeMap):
        #         # TODO: Is this a good place to determine if we Node-ify a value?
        #         log.debug(
        #             f"apply_value (off:{ctx.tell()}): Inside {self.current}. Set value to key {field.name}."
        #         )
        #         ctx.just_set_node = isinstance(value, pparse.Node)
        #         ctx.just_set_field = field
        #         self.current.value[field.name] = value
        #         return
        #     log.debug(
        #         f"UNLIKELY!! apply_value (off:{ctx.tell()}): Create arr as top level object."
        #     )
        #     breakpoint()
        # def _start_map_node(self, ctx: pparse.NodeContext, field: Any) -> None:
        #     ctx.mark_field_start()
        #     parent = self.current
        #     newmap = NodeMap(parent, ctx.reader(), proto.by_type_name(field.type_name))
        #     if isinstance(self.current, NodeArray):
        #         log.debug(
        #             f"start_map (off:{ctx.tell()}): Inside Array. Append new map to current array."
        #         )
        #         self.current.value.append(newmap)
        #         self.current = newmap
        #     elif isinstance(self.current, NodeMap):
        #         log.debug(
        #             f"start_map (off:{ctx.tell()}): Inside Map. Add new map to current map as {field.name}."
        #         )
        #         parent.value[field.name] = newmap
        #         self.current = parent.value[field.name]
        #     else:
        #         log.debug(
        #             f"start_map (off:{ctx.tell()}): Create map as top level object."
        #         )
        #         parent.value = newmap
        #         self.current = newmap
        def _end_container_node(self, ctx: pparse.NodeContext) -> None:
            parent = ctx._parent
            if parent:
                log.debug(
                    f"end_container (off:{ctx.tell()}): Backtracking to parent {parent}."
                )

                # Set the end pointer to advance parent past field.
                ctx.mark_end()

                # In parent, fast forward past the bit we just parsed.
                parent.ctx().seek(ctx._end)

                # Kill ctx (hopefully reclaiming memory).
                ctx.node().clear_ctx()

                # Set current node to parent.
                self.current = parent


        def scan_data(self) -> pparse.Parser:
            try:
                while True:
                    # While not end of data, keep parsing via states.
                    self.current.ctx().state().parse_data(self, self.current.ctx())
            except pparse.EndOfNodeException:
                pass
            except pparse.EndOfDataException:
                pass
            except pparse.UnsupportedFormatException:
                raise

            # TODO: Do all the children.

            return self

    return Parser

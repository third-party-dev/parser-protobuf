from __future__ import annotations

import logging
import struct
from typing import Any, Optional, Type

log = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(message)s')

import thirdparty.pparse.lib as pparse

# from thirdparty.pparse.lazy.flatbuffers.node import Node, NodeVector, NodeTable
from thirdparty.pparse.lazy.flatbuffers.state import (
    FlatbuffersParsingRootTableOffset,
    FlatbuffersParsingVTable,
    FlatbuffersParsingString,
    FlatbuffersParsingState,
)
from thirdparty.pparse.lazy.flatbuffers.meta import FlatbuffersSchema
from thirdparty.pparse.lazy.flatbuffers.node import NodeContext


# proto = OnnxPb()
def configure_pparser(**kwargs: Any) -> Type[pparse.Parser]:

    ext_list = ['.unknown']
    if 'ext_list' in kwargs:
        ext_list = kwargs['ext_list']

    json_schema = {}
    if 'json_schema' in kwargs:
        json_schema = kwargs['json_schema']

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
            # TODO: Look for TFL3 after root_table offset.
            return False


        def make_root_node(
            self,
            parent: Optional[pparse.Node] = None,
            init_state: Type[FlatbuffersParsingState] = FlatbuffersParsingRootTableOffset,
        ) -> pparse.Node:
            init_state = self._init_state_as_cls(init_state)

            root = pparse.Node(self._source.open(), self, default_value={}, parent=parent)
            root.ctx()._next_state(init_state)
            return root


        def __init__(self, source: pparse.Extraction, id: str = "flatbuffers") -> None:
            super().__init__(source, id, FlatbuffersParsingState)

            '''
            The top_reader is from the top of the file (req'd for flatbuffers).
            The Node's reader is from the start of the node.
            '''

            self.top_reader = source.open()
            self.schema = FlatbuffersSchema(schema_obj=json_schema)


        # Note: Expecting ctx.reader() to be at start of new node table.
        def new_node_table(self, node: pparse.Node, table_name: str) -> pparse.Node:
            node_table = pparse.Node(node.ctx().reader(), self, parent=node, ctx_class=NodeContext)
            node_table.ctx()._type_desc = self.schema.objects[table_name]
            node_table.ctx()._next_state(FlatbuffersParsingVTable)
            return node_table


        # Note: Expecting ctx.reader() to be at start of new node table.
        def new_node_string(self, node: pparse.Node) -> pparse.Node:
            node_str = pparse.Node(node.ctx().reader(), self, parent=node, ctx_class=NodeContext)
            node_str.ctx()._next_state(FlatbuffersParsingString)
            return node_str


        def new_node_table_idx(self, node: pparse.Node, table_idx: int) -> pparse.Node:
            node_table = pparse.Node(node.ctx().reader(), self, parent=node, ctx_class=NodeContext)
            node_table.ctx()._type_desc = self.schema.objects_by_index[table_idx]
            node_table.ctx()._next_state(FlatbuffersParsingVTable)
            return node_table


        def is_simple(self, type_desc: dict[str, Any]) -> bool:
            if 'fields' in type_desc:
                return False
            if 'type' in type_desc and 'base_type' in type_desc['type']:
                if type_desc['type']['base_type'].lower() in ['uint', 'string', 'bool', 'byte', 'int', 'float']:
                    return True
                if type_desc['type']['base_type'].lower() in ['vector', 'utype', 'union', 'obj']:
                    return False

            breakpoint()
            return False


        def peek_simple(self, ctx: pparse.NodeContext) -> Any:
            type_desc = ctx.type_desc()
            if type_desc['type']['base_type'].lower() == 'uint':
                return self.peek_u32(ctx)
            if type_desc['type']['base_type'].lower() == 'string':
                tmp = pparse.NodeContext(None, ctx.reader(), self)
                tmp.skip(self.peek_u32(tmp))
                return self.read_string(tmp)
            if type_desc['type']['base_type'].lower() == 'bool':
                return struct.unpack('?', ctx.peek(1))
            if type_desc['type']['base_type'].lower() == 'int':
                return self.peek_i32(ctx)
            if type_desc['type']['base_type'].lower() == 'float':
                return struct.unpack('<f', ctx.peek(4))[0]
            if type_desc['type']['base_type'].lower() == 'byte':
                return ctx.peek(1)
            breakpoint()


        # TODO: parse_table, parse_vtable, parse_field,
        #       parse_scalar, parse_vector, parse_union
        def read_u32(self, ctx: pparse.NodeContext, peek: bool = False) -> int:
            data = ctx.peek(4) if peek else ctx.read(4)
            if len(data) < 4:
                raise pparse.EndOfDataException("Not enough data in parse_u32()")
            return struct.unpack('<I', data)[0]


        def read_i32(self, ctx: pparse.NodeContext, peek: bool = False) -> int:
            # Get 32bit signed int (mostly for vtable offsets)
            data = ctx.peek(4) if peek else ctx.read(4)
            if len(data) < 4:
                raise pparse.EndOfDataException("Not enough data in parse_i32()")
            return struct.unpack('<i', data)[0]


        def peek_u32(self, ctx: pparse.NodeContext) -> int:
            return self.read_u32(ctx, peek=True)


        def peek_i32(self, ctx: pparse.NodeContext) -> int:
            return self.read_i32(ctx, peek=True)


        def read_u16(self, ctx: pparse.NodeContext, peek: bool = False) -> int:
            data = ctx.peek(2) if peek else ctx.read(2)
            if len(data) < 2:
                raise pparse.EndOfDataException("Not enough data in parse_u16()")
            return struct.unpack('<H', data)[0]


        def peek_u16(self, ctx: pparse.NodeContext) -> int:
            return self.read_u16(ctx, peek=True)


        def read_string(self, ctx: pparse.NodeContext) -> str:
            length = self.read_u32(ctx)
            data = ctx.read(length)
            log.debug(f"read_string(): len {length} data {data[:16]}")
            if len(data) < length:
                breakpoint()
                raise pparse.EndOfDataException("Not enough data in read_string()")
            return data.decode('utf-8')


        def read_scalar(self, ctx: pparse.NodeContext, base_type: str) -> Any:
            if base_type not in self.schema.TYPE_FORMATS:
                raise ValueError(f"Unsupported scalar type: {base_type}")
            size = self.schema.TYPE_SIZES[base_type]
            fmt = self.schema.TYPE_FORMATS[base_type]
            data = ctx.peek(size)
            if len(data) < size:
                raise pparse.EndOfDataException("Not enough data in read_scalar()")
            return struct.unpack(fmt, data)[0]


        def _parse_thing(self, ctx: pparse.NodeContext, peek: bool = False) -> tuple[int, int]:
            value = 0
            start = ctx.tell()

            # Do stuff

            end = ctx.tell()
            if peek:
                ctx.seek(start)
            return value, end - start


        def parse_thing(self, ctx: pparse.NodeContext) -> Any:
            return self._parse_varint(ctx, False)[0]


        def peek_thing(self, ctx: pparse.NodeContext) -> Any:
            return self._parse_varint(ctx, True)

    return Parser

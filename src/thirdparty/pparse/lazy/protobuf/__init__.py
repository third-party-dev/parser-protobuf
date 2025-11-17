#!/usr/bin/env python3

import sys
import os
import io
from typing import Optional

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.protobuf.meta import OnnxPb, Protobuf
from thirdparty.pparse.lazy.protobuf.node import Node, NodeMap, NodeArray
from thirdparty.pparse.lazy.protobuf.state import ProtobufParsingKey


def trace(*args, **kwargs):
    print(*args, **kwargs)
    pass


proto = OnnxPb()


class Parser(pparse.Parser):

    @staticmethod
    def match_extension(fname: str):
        if not fname:
            return False
        for ext in ['.onnx']:
            if fname.endswith(ext):
                return True
        return False


    @staticmethod
    def match_magic(cursor: pparse.Cursor):
        return False

    
    def __init__(self, source: pparse.Extraction, id: str):

        super().__init__(source, id)

        # Initial node is a map of type '.onnx.ModelProto'
        protobuf_type = proto.by_type_name('.onnx.ModelProto')
        self.current = NodeMap(None, source.open(), protobuf_type)
        source._result[id] = self.current

        self.nodes = {}


    def _parse_varint(self, ctx, peek=False):
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
        return value, end-start
    

    def parse_varint(self, ctx):
        return self._parse_varint(ctx, False)[0]


    def peek_varint(self, ctx):
        return self._parse_varint(ctx, True)


    def peek_varint_key(self, ctx):
        # Note: Key varints (by spec) ar always 32 bits (fields are 29 bits)
        current_pos = ctx.tell()
        value, key_length = self._parse_varint(ctx)
        wire_type = (value & 0x7)
        field_num = (value >> 3)
        value_length = None
        value_length_length = 0
        if wire_type == Protobuf.LEN:
            value_length, value_length_length = self._parse_varint(ctx)
        meta_length = key_length + value_length_length

        ctx.seek(current_pos)

        return wire_type, field_num, meta_length, value_length


    def parse_varint_key(self, ctx):
        value = self.parse_varint(ctx)
        return (value & 0x7), (value >> 3)


    def parse_i32(self, ctx, peek=False):
        data = None
        if peek:
            data = ctx.peek(4)
        else:
            data = ctx.read(4)
        if not data or len(data) < 4:
            msg = f"Not enough data to parse Protobuf I32 data. Offset: {ctx.tell()}"
            raise pparse.EndOfDataException(msg)
        return struct.unpack("<I", data)[0]


    def parse_i64(self, ctx, peek=False):
        data = None
        if peek:
            data = ctx.peek(8)
        else:
            data = ctx.read(8)
        if not data or len(data) < 8:
            msg = f"Not enough data to parse Protobuf I64 data. Offset: {ctx.tell()}"
            raise pparse.EndOfDataException(msg)
        return struct.unpack("<Q", data)[0]


    def _apply_value(self, ctx, field, value):
        if isinstance(self.current, NodeArray):
            trace(f"apply_value (off:{ctx.tell()}): Inside {self.current}. Append value.")
            self.current.value.append(value)
            return

        elif isinstance(self.current, NodeMap):
            
            # TODO: Is this a good place to determine if we Node-ify a value?

            trace(f"apply_value (off:{ctx.tell()}): Inside {self.current}. Set value to key {field.name}.")
            ctx.just_set_node = isinstance(value, Node)
            ctx.just_set_field = field
            self.current.value[field.name] = value
            return

        trace(f"UNLIKELY!! apply_value (off:{ctx.tell()}): Create arr as top level object.")
        breakpoint()


    def _start_map_node(self, ctx, field):
        
        ctx.mark_field_start()
        parent = self.current
        newmap = NodeMap(parent, ctx.reader(), proto.by_type_name(field.type_name))

        if isinstance(self.current, NodeArray):
            trace(f"start_map (off:{ctx.tell()}): Inside Array. Append new map to current array.")
            self.current.value.append(newmap)
            self.current = newmap
        elif isinstance(self.current, NodeMap):
            trace(f"start_map (off:{ctx.tell()}): Inside Map. Add new map to current map as {field.name}.")
            parent.value[field.name] = newmap
            self.current = parent.value[field.name]
        else:
            trace(f"start_map (off:{ctx.tell()}): Create map as top level object.")
            parent.value = newmap
            self.current = newmap


    def _end_container_node(self, ctx):
        parent = ctx._parent
        if parent:
            trace(f"end_container (off:{ctx.tell()}): Backtracking to parent {parent}.")

            # Set the end pointer to advance parent past field.
            ctx.mark_end()

            # In parent, fast forward past the bit we just parsed.
            parent.ctx().seek(ctx._end)

            # Kill ctx (hopefully reclaiming memory).
            ctx.node().clear_ctx()

            # Set current node to parent.
            self.current = parent

    
    def scan_data(self):

        try:
            while True:
                # While not end of data, keep parsing via states.
                self.current.ctx().state().parse_data(self, self.current.ctx())
        except pparse.EndOfNodeException as e:
            pass
        except pparse.EndOfDataException as e:
            pass
        except pparse.UnsupportedFormatException:
            raise

        # TODO: Do all the children.
        
        return self
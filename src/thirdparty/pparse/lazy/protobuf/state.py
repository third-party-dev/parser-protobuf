#!/usr/bin/env python3

from __future__ import annotations

import logging
import struct

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.protobuf.meta import Field, Protobuf
# from thirdparty.pparse.lazy.protobuf.node import Node, NodeArray, NodeContext, NodeMap
from thirdparty.pparse.lazy.protobuf.node import NodeContext

def unzigzag(v: int) -> int:
    return (v >> 1) ^ -(v & 1)


def zigzag_i32(n: int) -> int:
    return (n << 1) ^ (n >> 31)


def zigzag_i64(n: int) -> int:
    return (n << 1) ^ (n >> 63)


class ProtobufParsingState(object):
    def parse_data(self, node: pparse.Node) -> int:
        raise NotImplementedError()


class ProtobufParsingComplete(object):
    def parse_data(self, node: pparse.Node) -> int:
        return pparse.ASCEND


'''
Each field is tagged: `tag = (field_number << 3) | wire_type`
The wire type VARINT, I64, and I32 are "simple" inline values.
The wire type LEN includes strings, bytes, messages, packed repeated fields.
- These are where new nodes should come from.
SGROUP/EGROUP are theoretically unused, but likely would trigger additional nodes as well.

VARINT: [tag varint (VARINT)] [value varint]
LEN: [tag varint (LEN)] [byte_length varint] [bytes]
Packed: [tag varint (LEN)] [byte_length varint] [varint0] [varint1] [varintN]

parser._root._value['graph']._value['node'][0]._value['attribute'][0]._value['t']
'''

class ProtobufParsingSimplePacked(ProtobufParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        breakpoint()

        while ctx.tell() < ctx._length:
            node._value.append(parser.parse_varint(ctx))
        
        # We're done.
        ctx._next_state(ProtobufParsingComplete)
        return pparse.ASCEND


class ProtobufParsingWireTypeLen(ProtobufParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        if ctx._field.type == Field.TYPE_MESSAGE:
            ctx._next_state(ProtobufParsingTag)
            return pparse.AGAIN

        if ctx._field.type == Field.TYPE_BOOL:
            node._value = struct.unpack_from(f'{ctx.left()}?', ctx.peek(ctx.left()), 0)
            ctx.skip(ctx.left())

        if ctx._field.type == Field.TYPE_INT64:
            node._value = []
            while ctx.left() > 0:
                node._value.append(parser.parse_varint(ctx))

        if ctx._field.type not in [Field.TYPE_BOOL, Field.TYPE_MESSAGE, Field.TYPE_INT64]:
            breakpoint()

        ctx._next_state(ProtobufParsingComplete)
        return pparse.ASCEND
        

        # if ctx._field.type in Protobuf.inline_types:
        #     breakpoint()
        #     length = parser.parse_varint(ctx)
        #     pkd_node = pparse.Node(ctx.reader(), parser, default_value=[], parent=node, ctx_class=NodeContext)
        #     pkd_node.ctx()._type_desc = ctx._field
        #     # TODO: With the length, we could parse fields out breadth first.
        #     pkd_node.ctx()._length = length
        #     pkd_node.ctx()._next_state(ProtobufParsingSimplePacked)

        #     if field.is_repeated():
        #         breakpoint()

        #     node._value[field.name] = pkd_node
        #     node.ctx()._descendants.append(pkd_node)
        #     return pparse.AGAIN


class ProtobufParsingBytes(ProtobufParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        node._value = ctx.read(ctx.left())
        # We're done.
        ctx._next_state(ProtobufParsingComplete)
        return pparse.ASCEND


class ProtobufParsingWireTypeI32(ProtobufParsingState):
    # TODO: Split based on wire_type
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()
        breakpoint()


class ProtobufParsingTag(ProtobufParsingState):
    # TODO: Split based on wire_type
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        # TODO: While going through fields, we must not go past parent's length.
        # TODO: Ideally we'd construct ranges for each LEN and check ctx.left()
        # TODO: For the root table, we'd use the extraction data source length.

        if ctx.left() == 0:
            # We're done.
            ctx._next_state(ProtobufParsingComplete)
            return pparse.ASCEND

        # Get the tag data.
        wire_type, field_num = parser.parse_varint_key(ctx)
        field = ctx.type_desc().by_id(field_num)

        # if field.name == 'attribute':
        #     breakpoint()
        log.debug(f"ProtobufParsingKey: parsing {ctx.type_desc().type_name()} {field}")

        if wire_type == Protobuf.I32:
            data = ctx.read(4)
            if field.type == Field.TYPE_FLOAT:
                value = struct.unpack('<f', data)[0]
                if field.is_repeated():
                    log.debug(f"Appending value {value} to {field.name}")
                    node._value.setdefault(field.name, []).append(value)
                else:
                    log.debug(f"Setting value {value} to {field.name}")
                    node._value[field.name] = value
                return pparse.AGAIN

        if wire_type == Protobuf.VARINT:
            if field.type in Protobuf.inline_types:
                value = parser.parse_varint(ctx)
                if field.is_repeated():
                    log.debug(f"Appending value {value} to {field.name}")
                    node._value.setdefault(field.name, []).append(value)
                else:
                    log.debug(f"Setting value {value} to {field.name}")
                    node._value[field.name] = value
                return pparse.AGAIN

            # TODO: Add support for sint32/sint64 with zigzag here.
            breakpoint()
            return pparse.AGAIN

        if wire_type == Protobuf.LEN:
            length = parser.parse_varint(ctx)

            # At this point, cursor should be at start of LEN payload. Build a new range
            # that only encompasses the LEN data so we can use ctx.left().
            reader = pparse.Range(ctx.reader().cursor(), length)
            # node's reader must skip what sub-nodes will handle.
            ctx.skip(length)

            # ! UNLOADED_VALUEs in output may be coming from here.
            len_node = pparse.Node(reader, parser, parent=node, ctx_class=NodeContext)
            lctx = len_node.ctx()
            lctx._field = field

            if field.type == Field.TYPE_STRING:
                # Special case for strings
                value = lctx.read(lctx.left()).decode('utf-8')
                if field.is_repeated():
                    log.debug(f"Appending string to {field.name}, bytes left {lctx.left()}")
                    node._value.setdefault(field.name, []).append(value)
                else:
                    log.debug(f"Setting string to {field.name}, bytes left {lctx.left()}")
                    node._value[field.name] = value
                # Note: len_node is thrown away at this point.
                return pparse.AGAIN

            if field.type == Field.TYPE_MESSAGE:
                lctx._type_desc = parser.schema.by_type_name(field.type_name)
                # ! TODO: This doesn't feel right.
                len_node._value = {}
                lctx._next_state(ProtobufParsingTag)
            elif field.type == Field.TYPE_BYTES:
                # TODO: This could be deferred!
                lctx._next_state(ProtobufParsingBytes)
            else:
                lctx._next_state(ProtobufParsingWireTypeLen)

            if field.is_repeated():
                log.debug(f"Appending unloaded len node to {field.name}, bytes left {lctx.left()}")
                node._value.setdefault(field.name, []).append(len_node)
            else:
                log.debug(f"Setting unloaded len node to {field.name}, bytes left {lctx.left()}")
                node._value[field.name] = len_node

            # TODO: Optional, detect recursive=True?
            ctx._descendants.append(len_node)

            return pparse.AGAIN

        breakpoint()


# Example protobuf/onnx parse of GPT2.onnx
"""
        ModelProto
        08 07   ir_version = 7
        12 07   producer_name LEN: 7
            70 79 74 6f 72 63 68   = 'pytorch'
        1a 05   producer_version LEN: 5
            32 2e 30 2e 31   = '2.0.1'
    18: 3a 96 cc d8 b7 02 = GraphProto graph LEN: 653665814
    24:   0a 43 node[0] LEN: 67
    26:     0a 09 input LEN: 9
                69 6e 70 75 74 5f 69 64 73 input_ids
            12 1b output LEN: 27
                2f 74 72 61 6e 73 66 6f 72 6d 65 72 2f 53 68 61 70 65 5f 6f 75 74 70 75 74 5f 30
                /transformer/Shape_output
            1a 12 name LEN: 18
                2f 74 72 61 6e 73 66 6f 72 6d 65 72 2f 53 68 61 70 65 /transformer/Shape
            22 05 op_type LEN: 5
                53 68 61 70 65 = Shape
            0a 5b node[1] LEN: 91
            12 1e output LEN: 30
                2f 74 72 61 6e 73 66 6f 72 6d 65 72 2f 43 6f  /transformer/Constant_output_0
                6e 73 74 61 6e 74 5f 6f 75 74 70 75 74 5f 30
            1a 15 name LEN: 21
                2f 74 72 61 6e 73 66 6f 72 6d 65 72 2f 43 6f 6e 73 74 61 6e 74 ./transformer/Constant
            22 08 optype LEN: 8
                43 6f 6e 73 74 61 6e 74  Constant
            2a 18 AttributeProto attribute LEN: 24
                0a 05 name LEN: 5
                76 61 6c 75 65 'value'
                2a 0c TensorProto t LEN: 12
                10 - int32 data_type
                    07 - 7
                4a 08 raw_data LEN: 8
                    00 00 00 00 00 00 00 00
                a0 01 LEN: 1
                04 type = TENSOR
            0a 85 01 node[2] LEN: 133
            0a 1b input[0] LEN: 27
                2f 74 72 61 6e 73 66 6f 72 6d 65 72 2f 53 68 61 70 65 5f 6f 75 74 70 75 74 5f 30 '/transformer/Shape_output_0'
            0a 1e input[1] LEN: 30
                2f 74 72 61 6e 73 66 6f 72 6d 65 72 2f 43 6f 6e 73 74 61 6e 74 5f 6f 75 74 70 75 74 5f 30 '/transformer/Constant_output_0'
            12 1c output[0] LEN: 28
                2f 74 72 61 6e 73 66 6f 72 6d 65 72 2f 47 61 74 68 65 72 5f 6f 75 74 70 75 74 5f 30 '/transformer/Gather_output_0'
            1a 13 name LEN: 19
                2f 74 72 61 6e 73 66 6f 72 6d 65 72 2f 47 61 74 68 65 72  '/transformer/Gather'
            22 06 op_type LEN: 6
                47 61 74 68 65 72 'Gather'
            2a 0b attribute LEN: 11
                0a 04 name LEN: 4
                61 78 69 73 'axis'
                18 00 i = 0
                a0 01 type = FLOAT
                02 - ???

            0a 47 node[3] LEN: 71
            0a 09 input[0]
                69 6e 70 75 74 5f 69 64 73 input_ids
            12 ...
    00000150: ...
"""

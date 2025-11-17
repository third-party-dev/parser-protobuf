#!/usr/bin/env python3

import struct

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.protobuf.meta import OnnxPb, Field, Protobuf
from thirdparty.pparse.lazy.protobuf.node import Node, NodeContext, NodeMap, NodeArray


def trace(*args, **kwargs):
    print(*args, **kwargs)
    pass


def unzigzag(v):
    return (v >> 1) ^ -(v & 1)


def zigzag_i32(n):
    return (n << 1) ^ (n >> 31)


def zigzag_i64(n):
    return (n << 1) ^ (n >> 63)


class ProtobufParsingState(object):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        raise NotImplementedError()


# Example protobuf/onnx parse of GPT2.onnx
'''
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
'''


class ProtobufParsingKey(ProtobufParsingState):
    '''
        TODO: Things not done:
        - No zigzag support
        - No map support
        - No 2's complement
        - No signed vs unsigned
        - Needs heuristic guessing when pb2 can't help.
        - Deferred loading not tested.
        - No support for sgroup/egroup.
    '''
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):

        if ctx.left() == 0:
            if ctx._parent is None:
                raise pparse.EndOfDataException("Nothing more to process.")

            # XXX: Testing ways to grab flat list of nodes or tensors.
            if ctx.node().msgtype().name == 'NodeProto':
                #breakpoint()
                parser.nodes[ctx.node().value['name']] = ctx.node()
            
            parser._end_container_node(ctx)
            ctx._next_state(ProtobufParsingKey)
            return

        # Get the key data.
        wire_type, field_num, meta_length, value_length = parser.peek_varint_key(ctx)

        field = None
        if isinstance(ctx.node(), NodeMap):
            field = ctx.node().field_by_id(field_num)
        elif isinstance(ctx.node(), NodeArray):
            field = ctx._parent.field_by_id(field_num)
        else: #UNLIKELY
            breakpoint()

        trace(f"\nPROCESSING FIELD (off: {ctx.tell()} left: {ctx.left()}): {field.name}   {field.type_name}\n")

        if isinstance(parser.current, NodeArray) and \
                ctx.key() and field.name != ctx.key().name:
            # Pop NodeArray if complete, but not done with parent NodeMap.
            trace(f"Ending NodeArray for repeated field {ctx.key().name}")
            parser._end_container_node(ctx)
            return

        # The following things are in an array, set that up first.
        # Note: Assuming you can not do NodeArray.value = [NodeArray]
        if field.label == Field.LABEL_REPEATED and not isinstance(parser.current, NodeArray):
            trace(f"Creating NodeArray for repeated field {field.name}")

            ctx.mark_field_start()
            parent = parser.current
            # Note: ctx.reader() returns duplicate.
            # 'field' is more universal than 'msgtype' for array nodes
            newarr = NodeArray(parent, ctx.reader(), field)

            # Assuming array parent is always a map.
            parser.current.value[field.name] = newarr
            parser.current = parser.current.value[field.name]

            ctx._next_state(ProtobufParsingKey)
            return

        # Progress past the key.
        ctx.set_key(field)
        ctx.skip(meta_length)

        if field.type == Field.TYPE_MESSAGE and value_length:
            trace(f"  LENGTH: {value_length} (meta_length: {meta_length}) range: {ctx.tell()} - {ctx.tell()+value_length}")

            # Create the new node and make it active.
            parser._start_map_node(ctx, field)

            # Save the length of the message in the new node.
            parser.current.ctx().reinit(ctx.tell(), value_length)
            return

        if field.type == Field.TYPE_INT64 or field.type == Field.TYPE_INT32:
            # TODO: Should this handle 2's compliment?
            value = parser.parse_varint(ctx)
            parser._apply_value(ctx, field, value)
            ctx._next_state(ProtobufParsingKey)
            return

        if field.type == Field.TYPE_ENUM and wire_type == Protobuf.VARINT:
            # Get the length of the sub-message.
            enum = parser.parse_varint(ctx)
            parser._apply_value(ctx, field, enum)

            ctx._next_state(ProtobufParsingKey)
            return

        if field.type == Field.TYPE_FLOAT and wire_type == Protobuf.I32:            
            # Get the length of the sub-message.
            value = ctx.read(4)
            float_value = struct.unpack('<f', value)[0]
            parser._apply_value(ctx, field, float_value)

            ctx._next_state(ProtobufParsingKey)
            return

        if field.type == Field.TYPE_STRING and wire_type == Protobuf.LEN:
            data = ctx.read(value_length)
            if len(data) <= 40:
                trace(f'Whole String: {data}')
            else:
                trace(f'Part of String (length {len(data)}): {data.decode('utf-8')[:40]}')

            trace(f'String: {data}')
            if (value_length > 0 and not data) or len(data) < value_length:
                msg = "Not enough data to parse Protobuf LEN data. " \
                    f"Offset: {ctx.tell()} Read: {len(data)} of {value_length}"
                raise pparse.EndOfDataException(msg)
            parser._apply_value(ctx, field, data.decode('utf-8'))

            ctx._next_state(ProtobufParsingKey)
            return

        if field.type == Field.TYPE_BYTES:
            data = ctx.read(value_length)
            if len(data) <= 40:
                trace(f'All Bytes: {data}')
            else:
                trace(f'First Bytes (length {len(data)}): {data[:40]}')

            if (value_length > 0 and not data) or len(data) < value_length:
                msg = "Not enough data to parse Protobuf LEN data. " \
                    f"Offset: {ctx.tell()} Read: {len(data)} of {value_length}"
                raise pparse.EndOfDataException(msg)

            parser._apply_value(ctx, field, data)

            ctx._next_state(ProtobufParsingKey)
            return

        trace("UNKNOWN FIELD OR WIRE TYPE")
        breakpoint()
    
        msg = f"Not a valid Protobuf wire type. Type: {wire_type} ({Protobuf.wire_type_str[wire_type]})"
        raise pparse.UnsupportedFormatException(msg)


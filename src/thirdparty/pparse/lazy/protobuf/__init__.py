#!/usr/bin/env python3

import sys
import struct
import os
import io

from typing import Optional

from thirdparty.pparse.lib import EndOfDataException, EndOfNodeException, UnsupportedFormatException, Range
import thirdparty.pparse.lib as pparse
#from thirdparty.pparse.lib import Range, Node, Cursor, Data, Parser, Artifact

from thirdparty.pparse.lazy.protobuf.meta import OnnxPb, Field, Protobuf

from thirdparty.pparse.lazy.protobuf.node import (
    Node,
    NodeContext,
    #NodeInit,
    NodeMap,
    NodeArray
)


def trace(*args, **kwargs):
    print(*args, **kwargs)
    pass


proto = OnnxPb()


def unzigzag(v):
    return (v >> 1) ^ -(v & 1)

def zigzag_i32(n):
    return (n << 1) ^ (n >> 31)

def zigzag_i64(n):
    return (n << 1) ^ (n >> 63)


class ProtobufParsingState(object):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        raise NotImplementedError()


class ProtobufParsingLen(ProtobufParsingState):

    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):

        length = parser.parse_varint()
        print(f'  LEN VALUE {length}')
        # TODO: Is this the point we look up the key in proto to continue?

        data = parser.read(length)
        if not data or len(data) < length:
            msg = "Not enough data to parse Protobuf LEN data. " \
                f"Offset: {parser.tell()} Read: {len(data)} of {length}"
            raise EndOfDataException(msg)

        if len(data) < 16:
            print(f'  DATA: {data}')

        parser._next_state(ProtobufParsingKey)
        return


'''
    ProtobufParsingMeta
    - Handle container ending
    - Handle creating repeated
    - Handle key parse
    - Handle node creation

    ProtobufParsingValue






    
      
    > src/thirdparty/pparse/lazy/protobuf/__init__.py(150)parse_data()
    -> breakpoint()
    (Pdb) n
    > src/thirdparty/pparse/lazy/protobuf/__init__.py(151)parse_data()
    -> field = ctx._parent.field_by_id(field_num)
    (Pdb) field_num
    11
    (Pdb) ctx.node()
    NodeArray(_type=dim, value=list)
    (Pdb) ctx.node().ctx()._parent
    NodeMap(_type=TensorShapeProto, value=dict)
    (Pdb) ctx._parent
    NodeMap(_type=TensorShapeProto, value=dict)
    (Pdb) ctx._parent.ctx()._parent
    NodeMap(_type=Tensor, value=dict)
    (Pdb) ctx._parent.ctx()._parent.ctx()._parent
    NodeMap(_type=TypeProto, value=dict)
    (Pdb) ctx._parent.ctx()._parent.ctx()._parent.ctx()._parent
    NodeMap(_type=ValueInfoProto, value=dict)
    (Pdb) ctx._parent.ctx()._parent.ctx()._parent.ctx()._parent.ctx()._parent
    NodeArray(_type=input, value=list)
    (Pdb) ctx._parent.ctx()._parent.ctx()._parent.ctx()._parent.ctx()._parent.ctx()._parent
    NodeMap(_type=GraphProto, value=dict)


    message GraphProto {
    repeated NodeProto node = 1;
    string name = 2;
    repeated TensorProto initializer = 5;
    repeated SparseTensorProto sparse_initializer = 15;
    string doc_string = 10;
    repeated ValueInfoProto input = 11;
    repeated ValueInfoProto output = 12;
    repeated ValueInfoProto value_info = 13;
    repeated TensorAnnotation quantization_annotation = 14;
    repeated StringStringEntryProto metadata_props = 16;
    reserved 3, 4, 6 to 9;
    reserved "ir_version", "producer_version", "producer_tag", "domain";
    }

    Given the above debug session and GraphProto ... I *think* that ValueInfoProto
    is repeating, but repeating abruptly within a very deep parse. We currently don't
    have a nice way to unwind the stack. We assume that whatever the next field_num
    is, we can access it. This is very bad.



    NodeMap(ModelProto)
    [ir_version] = 7
    [producer_name] = pytorch
    [producer_version] = 2.0.1
    [graph] = NodeMap(GraphProto) -> LENGTH: 653665814
        [node] = NodeArray(NodeProto)
        [0] = NodeMap(NodeProto) -> LENGTH: 93
            [input] = NodeArray(STRING)
            [0] = input_ids -> LENGTH
            ? how to end ?
            [output] = NodeArray(STRING)
            [0] = /transformer/Shape_output_0
            ? how to end ?
            [name] = /transformer/Shape
            [op_type] = Shape
            ? how to end ?
        [1] = NodeMap(NodeProto)
            ...

ModelProto
  08 07   ir_version = 7
  12 07   producer_name LEN: 7
    70 79 74 6f 72 63 68   = 'pytorch'
  1a 05   producer_version LEN: 5
    32 2e 30 2e 31   = '2.0.1'
  3a 96 cc d8 b7 02 = GraphProto graph LEN: 653665814
    0a 43 node[0] LEN: 67
      0a 09 input LEN: 9
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
      2a 18 AttributeProto attribute LEN
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

*****************************************************************
**** PLAN: End container when Range is at the end of its range?
  - Initial NodeMap Range based on Extraction.
  - Assume all NodeMap's have a range.
  - NodeArray's will duplicate their NodeMap range (but have specific offset)
  - The idea is that subnodes will all implicitly know where their parents end
    because their range will always lie within the parents range.
  - TODO: Still need to differentiate between Node-ified values and plain scalars.
  - Consider, all values as nodes may make code more simple.

'''


class ProtobufParsingKey(ProtobufParsingState):

    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
       
        #trace(f"Offset: {ctx.tell()} Goal: {goal}")
        # TODO: How do we only pop container if the value was a Node?
        # len(ctx.key().type_name) == 0 - Detect value was a scalar (STRING, BYTES, ...).
        #   - Possible work around, but we may want to Node-ify a STRING or BYTES.
        # if ctx.tell() == ctx._end and ctx.just_set_node:
        #     parser._end_container_node(ctx)
        #     ctx._next_state(ProtobufParsingKey)
        #     return

        
        # TODO: Recursively check the ctx._end from current to root. If we find offset
        #       is equal to ctx._end, pop all containers to the target container's parent.
        current_offset = ctx.tell()
        if current_offset == 93:
            breakpoint()
        end_list = []
        def check_if_ancestor_end(current_ctx):
            end_list.append(current_ctx)
            if current_offset == current_ctx._end and False:
                for container_ctx in end_list:
                    parser._end_container_node(container_ctx)
                return True
            if current_ctx._parent:
                return check_if_ancestor_end(current_ctx._parent.ctx())
            return False
        if check_if_ancestor_end(ctx):
            return
            

        # Get the key data.
        wire_type, field_num, meta_length, value_length = parser.peek_varint_key(ctx)

        # ! BUG: Do not assume the next field is within parent node
        # ! Fix: Use LEN earlier.

        field = None
        if isinstance(ctx.node(), NodeMap):
            field = ctx.node().field_by_id(field_num)
        elif isinstance(ctx.node(), NodeArray):
            if ctx.tell() == 653663894:
                            #65366 5832
                breakpoint()
            field = ctx._parent.field_by_id(field_num)
        else: #UNLIKELY
            breakpoint()

        trace(f"PROCESSING FIELD (off: {ctx.tell()}): {field.name}   {field.type_name}")
        #breakpoint()


        if isinstance(parser.current, NodeArray) and \
            ctx.key() and field.name != ctx.key().name:
                #breakpoint()
                trace(f"Ending NodeArray for repeated field {ctx.key().name}")
                parser._end_container_node(ctx)
                return
        
        

        # The following things are in an array, set that up first.
        # Note: Assuming you can not do NodeArray.value = [NodeArray]
        if field.label == Field.LABEL_REPEATED and \
            not isinstance(parser.current, NodeArray):
                trace(f"Creating NodeArray for repeated field {field.name}")
                #proto.by_type_name(field.type_name) != parser.current.msgtype():

                ctx.mark_field_start()
                parent = parser.current
                newarr = NodeArray(parent, ctx.reader(), field)

                # Assuming array parent is always a map.
                parser.current.value[field.name] = newarr
                parser.current = parser.current.value[field.name]

                ctx._next_state(ProtobufParsingKey)
                return

        # Progress past the key.
        ctx.set_key(field)
        ctx.skip(meta_length)
        if value_length:
            ctx.set_remaining(value_length)

        if field.type == Field.TYPE_MESSAGE:

            if not value_length: # UNLIKELY
                breakpoint()

            trace(f"  LENGTH: {value_length} (meta_length: {meta_length})")
            # ! ctx.set_remaining(length)

            # Create the new node and make it active.
            parser._start_map_node(ctx, field)

            # Save the length of the message in the new node.
            parser.current.ctx()._end = parser.current.ctx().tell() + value_length
            
            #breakpoint()
            return

        if field.type == Field.TYPE_INT64 or field.type == Field.TYPE_INT32:
            # ! TODO: I don't like that we're doing values in ParsingKey state.
            #ctx._next_state(ProtobufParsingScalar)
            # TODO: Should this handle 2's compliment?
            value = parser.parse_varint(ctx)
            parser._apply_value(ctx, field, value)
            #ctx.node().value[field.name] = value
            #ctx.set_key(None)
            ctx._next_state(ProtobufParsingKey)
            return

        if field.type == Field.TYPE_BYTES:
            #  # Get the length of the sub-message.
            # length = -1
            # if wire_type == Protobuf.LEN:
            #     length = parser.parse_varint(ctx)
            # else:
            #     # UNLIKELY
            #     breakpoint()
            
            data = ctx.read(value_length)
            parser._apply_value(ctx, field, data)

            #ctx.node().value[field.name] = value
            #ctx.set_key(None)
            ctx._next_state(ProtobufParsingKey)
            return

        if field.type == Field.TYPE_ENUM:

             # Get the length of the sub-message.
            value = -1
            if wire_type == Protobuf.VARINT:
                enum = parser.parse_varint(ctx)
            else:
                # UNLIKELY
                breakpoint()
            
            parser._apply_value(ctx, field, value)

            #ctx.node().value[field.name] = value
            #ctx.set_key(None)
            ctx._next_state(ProtobufParsingKey)
            return

        if field.type == Field.TYPE_FLOAT:
            
             # Get the length of the sub-message.
            value = -1
            if wire_type == Protobuf.I32:
                value = ctx.read(4)
            else:
                # UNLIKELY
                breakpoint()

            float_value = struct.unpack('<f', value)[0]
            
            parser._apply_value(ctx, field, float_value)

            #ctx.node().value[field.name] = value
            #ctx.set_key(None)
            ctx._next_state(ProtobufParsingKey)
            return

        if field.type == Field.TYPE_STRING:
            if wire_type == Protobuf.LEN:
                # length = parser.parse_varint(ctx)
                data = ctx.read(value_length)
                trace(f'String: {data}')
                if not data or len(data) < value_length:
                    msg = "Not enough data to parse Protobuf LEN data. " \
                        f"Offset: {ctx.tell()} Read: {len(data)} of {value_length}"
                    raise EndOfDataException(msg)

                parser._apply_value(ctx, field, data.decode('utf-8'))
                #if isinstance(ctx.node().value, dict):
                #    ctx.node().value[field.name] = data.decode('utf-8')
                #elif isinstance(ctx.node().value, list):
                #    ctx.node().value.append(data.decode('utf-8'))
                #else: # UNLIKELY
                #    breakpoint()

                ctx._next_state(ProtobufParsingKey)
                return
            breakpoint()

        # TODO: Check if field is repeated?
        breakpoint()

        parser._next_state(ProtobufParsingValue)
        return
    
    def nothing():
        pass
        # if wire_type == Protobuf.VARINT:
        #     # Output everything to prove we can scan.
        #     print(self.dbg_geninfo_str(parser, field_num, wire_type))
        #     print(self.dbg_proto_str(parser, field_num, wire_type))
        #     value = parser.parse_varint()
        #     print(f'  VALUE: {value}')

        #     if field.name == 'node':
        #         breakpoint()

        #     parser._next_state(ProtobufParsingKey)
        #     return

        # if wire_type == Protobuf.I64:
        #     # Output everything to prove we can scan.
        #     print(self.dbg_geninfo_str(parser, field_num, wire_type))
        #     print(self.dbg_proto_str(parser, field_num, wire_type))
        #     value = parser.parse_i64()
        #     print(f'  VALUE: {value}')
        #     parser._next_state(ProtobufParsingKey)

        # if wire_type == Protobuf.I32:
        #     # Output everything to prove we can scan.
        #     print(self.dbg_geninfo_str(parser, field_num, wire_type))
        #     print(self.dbg_proto_str(parser, field_num, wire_type))
        #     value = parser.parse_i32()
        #     print(f'  VALUE: {value}')
        #     parser._next_state(ProtobufParsingKey)
    
        # if wire_type == Protobuf.LEN:
        #     # As a LEN, this can be a SubMessage, String, Bytes, Repeated, or Packed

        #     # Output everything to prove we can scan.
        #     print(self.dbg_geninfo_str(parser, field_num, wire_type))
        #     print(self.dbg_proto_str(parser, field_num, wire_type))

        #     length = parser.parse_varint()
        #     print(f'  LENGTH: {length}')

        #     if field.type == Field.TYPE_STRING:
        #         data = parser.read(length)
        #         if not data or len(data) < length:
        #             msg = "Not enough data to parse Protobuf LEN data. " \
        #                 f"Offset: {parser.tell()} Read: {len(data)} of {length}"
        #             raise EndOfDataException(msg)

        #         if len(data) < 100:
        #             try:
        #                 print(f'  DATA: "{data.decode('utf-8')}"')
        #             except UnicodeDecodeError:
        #                 print(f'  rDATA: {data}')
                
        #         parser._next_state(ProtobufParsingKey)
        #         return
    
        #     else:
        #         print("-- skipping non-submessage LEN entry for now --")

        #         skipped = parser.skip(length)
        #         if skipped < length:
        #             msg = "Not enough data to parse Protobuf LEN data. " \
        #                 f"Offset: {parser.tell()} Read: {len(data)} of {length}"
        #             raise EndOfDataException(msg)

        #         parser._next_state(ProtobufParsingKey)
        #         return

            

        # # if wire_type == Protobuf.SGROUP:
        # #     parser._next_state(ProtobufParsingVarint)
        # #     raise NotImplementedError()
        
        # # if wire_type == Protobuf.EGROUP:
        # #     parser._next_state(ProtobufParsingVarint)
        # #     raise NotImplementedError()

        # raise UnsupportedFormatException(f"Not a valid Protobuf wire type. Type: {wire_type} ({Protobuf.wire_type_str[wire_type]})")


    def dbg_geninfo_str(self, parser, field_num, wire_type):
        return f'{field_num} (FIELD)\n  TYPE: {Protobuf.wire_type_str[wire_type]}'


    def dbg_proto_str(self, parser, field_num, wire_type):
        type_entry = parser.current_type()
        field = proto.by_type_name(type_entry.type_name).by_id(field_num)
        out = [
            f'  CONTAINER: {type_entry.type_name}',
            f'  FIELD_NAME: {field.name}',
            f'  FIELD_TYPE: {field.type_str()}',
        ]
        if field.type == 11:
            out.append(f'  FIELD_MSG_TYPE: {field.type_name}')
        return '\n'.join(out)







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


    # def current_type_repeated(self, field):
    #     cur_field = self.current_type().field
    #     return cur_field == field and cur_field.label == Field.LABEL_REPEATED


    def _parse_varint(self, ctx, peek=False):
        value = 0
        shift = 0
        start = ctx.tell()

        while True:
            u8 = ctx.read(1)
            if not u8 or len(u8) < 1:
                raise EndOfDataException(f"Not enough data to parse Protobuf varint. Offset: {ctx.tell()}")
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


    # def parse_varint(self, ctx):
    #     value, length = self.peek_varint(ctx)
    #     ctx.skip(length)
    #     return value


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
            raise EndOfDataException(f"Not enough data to parse Protobuf I32 data. Offset: {ctx.tell()}")
        return struct.unpack("<I", data)[0]


    def parse_i64(self, ctx, peek=False):
        data = None
        if peek:
            data = ctx.peek(8)
        else:
            data = ctx.read(8)
        if not data or len(data) < 8:
            raise EndOfDataException(f"Not enough data to parse Protobuf I64 data. Offset: {ctx.tell()}")
        return struct.unpack("<Q", data)[0]


    def _apply_value(self, ctx, field, value):
        if isinstance(self.current, NodeArray):
            trace(f"apply_value (off:{ctx.tell()}): Inside Array. Append value.")
            self.current.value.append(value)
            return

        elif isinstance(self.current, NodeMap):
            
            # TODO: Is this a good place to determine if we Node-ify a value?

            trace(f"apply_value (off:{ctx.tell()}): Inside Map. Set value to key {field.name}.")
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

    def _start_array_node(self, ctx, field):
        
        ctx.mark_field_start()
        parent = self.current
        newarr = NodeArray(parent, ctx.reader(), proto.by_type_name(field.type_name))

        if isinstance(self.current, NodeMap):
            trace(f"start_arr (off:{ctx.tell()}): Inside Map. Add new arr to current map as {field.name}.")
            self.current.value[field.name] = newarr
            self.current = self.current.value[field.name]

        elif isinstance(self.current, NodeArray):
            trace(f"UNLIKELY!! start_arr (off:{ctx.tell()}): Inside Array. Append new arr to current array.")
            breakpoint()
            
            self.current.value.append(newarr)
            self.current = newarr
        else:
            trace(f"UNLIKELY!! start_arr (off:{ctx.tell()}): Create arr as top level object.")
            breakpoint()

            self.current = newarr


    def _end_container_node(self, ctx):
        #breakpoint()
        parent = ctx._parent
        if parent:
            trace(f"end_container (off:{ctx.tell()}): Backtracking to parent.")

            # Set the end pointer to advance parent past field.
            # Note: We don't need to mark end in protobuf
            ctx.mark_end()

            # Fast forward past the bit we just parsed.
            parent.ctx().seek(ctx._end)

            # Kill ctx (hopefully reclaiming memory).
            ctx.node().clear_ctx()

            # Set current node to parent.
            self.current = parent


    
    def scan_data(self):

        # While not end of data, keep parsing via states.
        try:
            while True:
                #                                    (parser, ctx )
                self.current.ctx().state().parse_data(self, self.current.ctx())
        except EndOfNodeException as e:
            pass
        except EndOfDataException as e:
            pass
        except UnsupportedFormatException:
            raise

        # TODO: Do all the children.
        
        return self
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


# class ProtobufParsingMessage(ProtobufParsingState):

#     def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):

#         # Get the key data.
#         wire_type, field_num = parser.parse_varint_key()
#         field = parser.current_type_field(field_num)

#         # Length follows VARINT and LEN wire types.
#         length = parser.parse_varint()

#         # Are we a new type?
#         if not parser.current_type_matches(field):
            



#         # Register new message as current type in parser.
#         parser.push_type(field, length)

        


#         #


class ProtobufParsingKey(ProtobufParsingState):

    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):

        breakpoint()
        if ctx.tell() == ctx._end:
            parser._end_container_node(ctx)
            ctx._next_state(ProtobufParsingKey)
            return

        # Get the key data.
        wire_type, field_num, key_length = parser.peek_varint_key(ctx)
        field = ctx.node().field_by_id(field_num)
        ctx.set_key(field)
        ctx.skip(key_length)

        trace(f"PROCESSING FIELD: {field.name}")

        # Now that we have a value, lets process values and/or messages.
        if field.type == Field.TYPE_MESSAGE:

            # ! Handle repeated: field.label == Field.LABEL_REPEATED
            # ! Repeated should _start_array_node then _start_map_node for each element

            #print(self.dbg_geninfo_str(parser, field_num, wire_type))
            #print(self.dbg_proto_str(parser, field_num, wire_type))
            print(f"--- ProtobufParsingMessage: {field.type_name} ---")

            # TODO: Think this through ... how do we get to _end_container?

            # Get the length of the sub-message.
            length = -1
            if wire_type == Protobuf.LEN:
                length = parser.parse_varint(ctx)
            else:
                breakpoint()

            # Create the new node and make it active.
            parser._start_map_node(ctx, field)

            # Save the length of the message in the new node.
            parser.current.ctx()._end = parser.current.ctx().tell() + length
            
            #breakpoint()
            return

        if field.type == Field.TYPE_INT64:
            # ! TODO: I don't like that we're doing values in ParsingKey state.
            #ctx._next_state(ProtobufParsingScalar)
            # TODO: Should this handle 2's compliment?
            value = parser.parse_varint(ctx)
            ctx.node().value[field.name] = value
            ctx.set_key(None)
            ctx._next_state(ProtobufParsingKey)
            return

        if field.type == Field.TYPE_STRING:
            if wire_type == Protobuf.LEN:
                length = parser.parse_varint(ctx)
                data = ctx.read(length)
                if not data or len(data) < length:
                    msg = "Not enough data to parse Protobuf LEN data. " \
                        f"Offset: {ctx.tell()} Read: {len(data)} of {length}"
                    raise EndOfDataException(msg)
                ctx.node().value[field.name] = data.decode('utf-8')
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



class ProtobufParsingField(ProtobufParsingState):

    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):



        if not ctx.key():
            parser._next_state(ProtobufParsingKey)
            return

        

        # Get the key data.
        wire_type, field_num, key_length = parser.peek_varint_key(ctx)
        field = ctx.node().field_by_id(field_num)
        ctx.set_key(field)
        ctx.skip(key_length)

        # Now that we have a value, lets process values and/or messages.
        if field.type == Field.TYPE_MESSAGE:
            print(self.dbg_geninfo_str(parser, field_num, wire_type))
            print(self.dbg_proto_str(parser, field_num, wire_type))
            print(f"--- ProtobufParsingMessage: {field.type_name} ---")
            parser._start_map_node(ctx)
            return

        if field.type == Field.TYPE_INT64:
            ctx._next_state(ProtobufParsingScalar)
            # TODO: Should this handle 2's compliment?
            value, length = parser.parse_varint(ctx)
            ctx.node().value[field.name] = value

        # TODO: Check if field is repeated?
        breakpoint()

        parser._next_state(ProtobufParsingValue)
        return



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


    def parse_varint(self, ctx, peek=False):
        value = 0
        shift = 0
        offset = 0
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
        
        if peek:
            ctx.seek(start)
        return value
    

    def peek_varint(self, ctx):
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
        ctx.seek(start)
        return value, end-start


    def parse_varint(self, ctx):
        value, length = self.peek_varint(ctx)
        ctx.skip(length)
        return value


    def peek_varint_key(self, ctx):
        # Note: Key varints (by spec) ar always 32 bits (fields are 29 bits)
        value, length = self.peek_varint(ctx)
        return (value & 0x7), (value >> 3), length


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


    def _start_map_node(self, ctx, field):
        
        ctx.mark_field_start()
        parent = self.current
        newmap = NodeMap(parent, ctx.reader(), proto.by_type_name(field.type_name))
        
        if ctx.key():
            trace(f"start_map (off:{ctx.tell()}): Found key, assuming in Map. Add new map to current map.")
            parent.value[field.name] = newmap
            self.current = parent.value[field.name]
        elif isinstance(self.current, NodeArray):
            trace(f"start_map (off:{ctx.tell()}): Inside Array. Append new map to current array.")
            self.current.value.append(newmap)
            self.current = newmap
        else:
            trace(f"start_map (off:{ctx.tell()}): Create map as top level object.")
            parent.value = newmap
            self.current = newmap

    # def _start_array_node(self, ctx):
        
    #     newarr = NodeArray(self.current, ctx.reader())

    #     if ctx.field():
    #         trace(f"start_arr (off:{ctx.tell()}): Found key, assuming in Map. Add new arr to current map.")
    #         self.current.value[ctx.key()] = newarr
    #         self.current = self.current.value[ctx.key()]
    #         ctx.set_key(None)
    #     elif isinstance(self.current, NodeArray):
    #         trace(f"start_arr (off:{ctx.tell()}): Inside Array. Append new arr to current array.")
    #         self.current.value.append(newarr)
    #         self.current = newarr
    #     else:
    #         trace(f"start_arr (off:{ctx.tell()}): Create arr as top level object.")
    #         self.current = newarr


    def _end_container_node(self, ctx):
        parent = ctx._parent
        if parent:
            trace(f"end_container (off:{ctx.tell()}): Backtracking to parent.")

            # Set the end pointer to advance parent past field.
            # Note: We don't need to mark end in protobuf
            #ctx.mark_end()

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
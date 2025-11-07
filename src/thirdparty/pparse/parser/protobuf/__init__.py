#!/usr/bin/env python3

import sys
import struct
import os
import io

from typing import Optional

from thirdparty.pparse.lib import EndOfDataException, UnsupportedFormatException, Range
import thirdparty.pparse.lib as pparse
#from thirdparty.pparse.lib import Range, Node, Cursor, Data, Parser, Artifact

from thirdparty.pparse.cli.parse_pb import OnnxPb, Field
proto = OnnxPb()


def unzigzag(v):
    return (v >> 1) ^ -(v & 1)

def zigzag_i32(n):
    return (n << 1) ^ (n >> 31)

def zigzag_i64(n):
    return (n << 1) ^ (n >> 63)


class Protobuf():
    VARINT = 0
    I64 = 1
    LEN = 2
    SGROUP = 3
    EGROUP = 4
    I32 = 5

    FALSE = 0
    TRUE = 1

    wire_type_str = {
        0: "VARINT",
        1: "I64",
        2: "LEN",
        3: "SGROUP",
        4: "EGROUP",
        5: "I32",
    }


class ProtobufParsingState(object):
    def parse_data(self, parser: 'ProtobufParser'):
        raise NotImplementedError()


class ProtobufParsingLen(ProtobufParsingState):

    def parse_data(self, parser: 'ProtobufParser'):

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


class ProtobufParsingKey(ProtobufParsingState):

    def parse_data(self, parser: 'ProtobufParser'):

        # Get the key data.
        wire_type, field_num = parser.parse_varint_key()

        if wire_type == Protobuf.VARINT:
            # Output everything to prove we can scan.
            print(self.dbg_geninfo_str(parser, field_num, wire_type))
            print(self.dbg_proto_str(parser, field_num, wire_type))
            value = parser.parse_varint()
            print(f'  VALUE {value}')
            parser._next_state(ProtobufParsingKey)
            return

        if wire_type == Protobuf.I64:
            # Output everything to prove we can scan.
            print(self.dbg_geninfo_str(parser, field_num, wire_type))
            print(self.dbg_proto_str(parser, field_num, wire_type))
            value = parser.parse_i64()
            print(f'  VALUE {value}')
            parser._next_state(ProtobufParsingKey)

        if wire_type == Protobuf.I32:
            # Output everything to prove we can scan.
            print(self.dbg_geninfo_str(parser, field_num, wire_type))
            print(self.dbg_proto_str(parser, field_num, wire_type))
            value = parser.parse_i32()
            print(f'  VALUE {value}')
            parser._next_state(ProtobufParsingKey)
        
        if wire_type == Protobuf.LEN:
            # As a LEN, this can be a SubMessage, String, Bytes, Repeated, or Packed

            # Output everything to prove we can scan.
            print(self.dbg_geninfo_str(parser, field_num, wire_type))
            print(self.dbg_proto_str(parser, field_num, wire_type))

            length = parser.parse_varint()
            print(f'  LENGTH: {length}')

            field = proto.by_type_name(parser.current_type().type_name).by_id(field_num)

            if field.type == 11: # TYPE_MESSAGE
                parser.push_type(field.type_name, length)
                print(f"--- {field.type_name} ---")
            
            elif field.type == 9: # TYPE_STRING
                data = parser.read(length)
                if not data or len(data) < length:
                    msg = "Not enough data to parse Protobuf LEN data. " \
                        f"Offset: {parser.tell()} Read: {len(data)} of {length}"
                    raise EndOfDataException(msg)

                if len(data) < 100:
                    try:
                        print(f'  DATA: "{data.decode('utf-8')}"')
                    except UnicodeDecodeError:
                        print(f'  rDATA: {data}')
    
            else:
                print("-- skipping non-submessage LEN entry for now --")

                skipped = parser.skip(length)
                if skipped < length:
                    msg = "Not enough data to parse Protobuf LEN data. " \
                        f"Offset: {parser.tell()} Read: {len(data)} of {length}"
                    raise EndOfDataException(msg)

            parser._next_state(ProtobufParsingKey)
            return

        # if wire_type == Protobuf.SGROUP:
        #     parser._next_state(ProtobufParsingVarint)
        #     raise NotImplementedError()
        
        # if wire_type == Protobuf.EGROUP:
        #     parser._next_state(ProtobufParsingVarint)
        #     raise NotImplementedError()


        raise UnsupportedFormatException(f"Not a valid Protobuf wire type. Type: {wire_type} ({Protobuf.wire_type_str[wire_type]})")


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


class TypeStackEntry():
    def __init__(self, parser, type_name, length):
        self.type_name = type_name
        if length == -1:
            self.range = parser.cursor().dup()
        else:
            self.range = Range(parser.cursor(), length)


class ProtobufParser(pparse.Parser):

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

    
    def __init__(self, artifact: pparse.Artifact, id: str):
        super().__init__(artifact, id)

        self.state: Optional[ProtobufParsingState] = ProtobufParsingKey()

        self._type_stack = [TypeStackEntry(self, '.onnx.ModelProto', -1)]

        # self.num_bytes = []
        # self.str_bytes = [b'"']
        # self.json_ref = None
        # self.current = None
        # self.stack = []
        # self.key_reg = None

    def _next_state(self, state: ProtobufParsingState):
        self.state = state()


    def current_type(self):
        return self._type_stack[-1]


    def push_type(self, type_name, length):
        self._type_stack.append(TypeStackEntry(self, type_name, length))
        return self.current_type()

    
    def pop_type(self):
        return self._type_stack.pop()


    # Convienence Aliases
    def tell(self):
        return self.current_type().range._cursor.tell()
    def seek(self, offset):
        return self.current_type().range.seek(offset)
    def skip(self, length):
        return self.current_type().range.skip(length)
    def peek(self, length):
        return self.current_type().range.peek(length)
    def read(self, length, mode=None):
        return self.current_type().range.read(length, mode=mode)




    def parse_varint(self):
        value = 0
        shift = 0
        offset = 0

        while True:
            u8 = self.read(1)
            if not u8 or len(u8) < 1:
                raise EndOfDataException(f"Not enough data to parse Protobuf varint. Offset: {self.tell()}")
            u8 = ord(u8)
            value |= (u8 & 0x7F) << shift
            if not (u8 & 0x80):
                break
            shift += 7
        return value

    def parse_varint_key(self):
        value = self.parse_varint()
        return (value & 0x7), (value >> 3)

    def parse_length(self):
        length = self.parse_varint()
        # Is this raw data? # Do we need to key to know?
        data = self.read(length)
        if not data or len(data) < length:
            raise EndOfDataException(f"Not enough data to parse Protobuf LEN data. Offset: {self.tell()}")
        return data

    def parse_i32(self):
        data = self.read(4)
        if not data or len(data) < length:
            raise EndOfDataException(f"Not enough data to parse Protobuf I32 data. Offset: {self.tell()}")
        return struct.unpack("<I", data)[0]

    def parse_i64(self):
        data = self.read(8)
        if not data or len(data) < length:
            raise EndOfDataException(f"Not enough data to parse Protobuf I64 data. Offset: {self.tell()}")
        return struct.unpack("<Q", data)[0]


    # def _apply_value(self, value):
    #     if self.key_reg:
    #         self.current[self.key_reg] = value
    #         self.key_reg = None
    #     elif isinstance(self.current, list):
    #         self.current.append(value)
    #     elif isinstance(self.current, dict) and self.key_reg == None:
    #         self.key_reg = value
    #     else:
    #         self.current = value
    #         self._meta['root'] = self.current
    
    # def _start_map(self):
    #     self.stack.append(self.current)
    #     if self.key_reg:
    #         self.current[self.key_reg] = {}
    #         self.current = self.current[self.key_reg]
    #         self.key_reg = None
    #     elif isinstance(self.current, list):
    #         self.current.append({})
    #         self.current = self.current[-1]
    #     else:
    #         self.current = {}
    #         self._meta['root'] = self.current

    # def _start_array(self):
    #     self.stack.append(self.current)
    #     if self.key_reg:
    #         self.current[self.key_reg] = []
    #         self.current = self.current[self.key_reg]
    #         self.key_reg = None
    #     elif isinstance(self.current, list):
    #         self.current.append([])
    #         self.current = self.current[-1]
    #     else:
    #         self.current = []
    #         self._meta['root'] = self.current

    # def _end_container(self):
    #     if len(self.stack) > 1:
    #         self.current = self.stack.pop()
    #         self._meta['root'] = self.current
    
    def eagerly_parse(self):

        exc_store = None
        try:
            #breakpoint()
            #print(f"{self.state}.parse_data()")
            while True:
                self.state.parse_data(self)
        except EndOfDataException as e:
            if not exc_store:
                exc_store = e
        except UnsupportedFormatException:
            raise

        for child in self.children:
            try:
                child.scan_data()
            except EndOfDataException as e:
                if not exc_store:
                    exc_store = e

        if exc_store:
            raise exc_store

        return self


    def scan_data(self):
        return self.eagerly_parse()
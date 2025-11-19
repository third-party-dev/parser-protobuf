#!/usr/bin/env python3

import sys
import struct
import zlib
import os
import urllib.parse
import io
import tarfile
import ijson

import argparse

class PickleParsingState():
    def parse_data(self, context: PObjParser):
        raise NotImplementedError()


class PklOp():
    MARK = 40
    STOP = 0x2e
    PROTO = 0x80
    LONG1 = 0x8a
    POP = 48
    POP_MARK = 49
    DUP = 50
    FLOAT = 70
    INT = 73
    BININT = 74
    BININT1 = 75
    LONG = 76
    BININT2 = 77
    NONE = 78
    PERSID = 80
    BINPERSID = 81
    REDUCE = 82
    STRING = 83
    BINSTRING = 84
    SHORT_BINSTRING = 85
    UNICODE = 86
    BINUNICODE = 88
    APPEND = 97
    BUILD = 98
    GLOBAL = 99
    DICT = 100
    EMPTY_DICT = 125
    APPENDS = 101
    GET = 103
    BINGET = 104
    INST = 105
    LONG_BINGET = 106
    LIST = 108
    EMPTY_LIST = 93
    OBJ = 111
    PUT = 112
    BINPUT = 113
    LONG_BINPUT = 114
    SETITEM = 115
    TUPLE = 116
    EMPTY_TUPLE = 41
    SETITEMS = 117
    BINFLOAT = 71

    # Proto 2
    NEWOBJ = 129
    EXT1 = 130
    EXT2 = 131
    EXT4 = 132
    TUPLE1 = 133
    TUPLE2 = 134
    TUPLE4 = 135
    NEWTRUE = 136
    NEWFALSE = 137
    LONG1 = 138
    LONG4 = 139

    # Proto 3
    BINBYTES = 66
    SHORT_BINBYTES = 67

    # Proto 4
    SHORT_BINUNICODE = 140
    BINUNICODE8 = 141
    BINBYTES8 = 142
    EMPTY_SET = 143
    ADDITEMS = 144
    FROZENSET = 145
    NEWOBJ_EX = 146
    STACK_GLOBAL = 147
    MEMOIZE = 148
    #FRAME = 149

    # Proto 5
    BYTEARRAY8 = 150
    NEXT_BUFFER = 151
    READONLY_BUFFER = 152

    @staticmethod
    def ins_def(alias, lbytes=0, pbytes=0, fmt=''):
        return {
            'alias': alias,
            'lbytes': lbytes,
            'pbytes': pbytes,
            'fmt': fmt,
        }

    _mapping_dict = {
        # alias
        # lbytes - size of length prefix
        # pbytes - size of parameter
        # fmt - everything is little endian if not READLINE
        #   - if 'R', its readline, otherwise its the struct.unpack fmt

        0x28: PklOp.ins_def("MARK"),
        0x29: PklOp.ins_def("EMPTY_TUPLE"),
        0x2e: PklOp.ins_def("STOP"),
        0x30: PklOp.ins_def("POP"),
        0x31: PklOp.ins_def("POP_MARK"),
        0x32: PklOp.ins_def("DUP"),
        0x4e: PklOp.ins_def("NONE"),
        0x51: PklOp.ins_def("BINPERSID"),
        0x52: PklOp.ins_def("REDUCE"),
        0x5d: PklOp.ins_def("EMPTY_LIST"),
        0x61: PklOp.ins_def("APPEND"),
        0x62: PklOp.ins_def("BUILD"),
        0x64: PklOp.ins_def("DICT"),
        0x65: PklOp.ins_def("APPENDS"),
        0x6c: PklOp.ins_def("LIST"),
        0x6f: PklOp.ins_def("OBJ"),
        0x73: PklOp.ins_def("SETITEM"),
        0x74: PklOp.ins_def("TUPLE"),
        0x75: PklOp.ins_def("SETITEMS"),
        0x7d: PklOp.ins_def("EMPTY_DICT"),
        0x81: PklOp.ins_def("NEWOBJ"),
        0x85: PklOp.ins_def("TUPLE1"),
        0x86: PklOp.ins_def("TUPLE2"),
        0x87: PklOp.ins_def("TUPLE3"),
        0x88: PklOp.ins_def("NEWTRUE"),
        0x89: PklOp.ins_def("NEWFALSE"),
        0x8f: PklOp.ins_def("EMPTY_SET"),
        0x90: PklOp.ins_def("ADDITEMS"),
        0x91: PklOp.ins_def("FROZENSET"),
        0x92: PklOp.ins_def("NEWOBJ_EX"),
        0x93: PklOp.ins_def("STACK_GLOBAL"),
        # ! TODO: SIZE?
        0x94: PklOp.ins_def("MEMOIZE"),
        0x97: PklOp.ins_def("NEXT_BUFFER"),
        0x98: PklOp.ins_def("READONLY_BUFFER"),

        # Readline delimited
        0x46: PklOp.ins_def("FLOAT", fmt='R'),
        0x49: PklOp.ins_def("INT", fmt='R'),
        0x4c: PklOp.ins_def("LONG", fmt='R'),
        0x50: PklOp.ins_def("PERSID", fmt='R'),
        0x53: PklOp.ins_def("STRING", fmt='R'),
        0x56: PklOp.ins_def("UNICODE", fmt='R'),
        0x63: PklOp.ins_def("GLOBAL", fmt='R'),
        0x67: PklOp.ins_def("GET", fmt='R'),
        0x69: PklOp.ins_def("INST", fmt='R'),
        0x70: PklOp.ins_def("PUT", fmt='R'),

        # Static Sized Params
        0x47: PklOp.ins_def("BINFLOAT", pbytes=8, fmt='<d'),
        0x4a: PklOp.ins_def("BININT", pbytes=4, fmt='<i'),
        0x4b: PklOp.ins_def("BININT1", pbytes=1, fmt='b'),
        0x4d: PklOp.ins_def("BININT2", pbytes=2, fmt='<h'),
        0x55: PklOp.ins_def("SHORT_BINSTRING", lbytes=1, fmt='B'),
        0x68: PklOp.ins_def("BINGET", pbytes=1, fmt='B'),
        0x6a: PklOp.ins_def("LONG_BINGET", pbytes=4, fmt='<i'),
        0x71: PklOp.ins_def("BINPUT", pbytes=1, fmt='B'),
        0x72: PklOp.ins_def("LONG_BINPUT", pbytes=4, fmt='<i'),
        0x80: PklOp.ins_def("PROTO", pbytes=1, fmt='B'),
        0x82: PklOp.ins_def("EXT1", pbytes=1, fmt='B'),
        0x83: PklOp.ins_def("EXT2", pbytes=2, fmt='<h'),
        0x84: PklOp.ins_def("EXT4", pbytes=4, fmt='<i'),
        0x95: PklOp.ins_def("FRAME", pbytes=8, fmt='<q'),

        # Length Prefixed Params
        0x42: PklOp.ins_def("BINBYTES", lbytes=4, fmt='<i'),
        0x43: PklOp.ins_def("SHORT_BINBYTES", lbytes=1, fmt='B'),
        0x54: PklOp.ins_def("BINSTRING", lbytes=4, fmt='<i'),
        0x58: PklOp.ins_def("BINUNICODE", lbytes=4, fmt='<i'),
        0x8a: PklOp.ins_def("LONG1", lbytes=1, fmt='B'),
        0x8b: PklOp.ins_def("LONG4", lbytes=4, fmt='<i'),
        0x8c: PklOp.ins_def("SHORT_BINUNICODE", lbytes=1, fmt='B'),
        0x8d: PklOp.ins_def("BINUNICODE8", lbytes=8, fmt='<q'),
        0x8e: PklOp.ins_def("BINBYTES8", lbytes=8, fmt='<q'),
        0x96: PklOp.ins_def("BYTEARRAY8", lbytes=8, fmt='<q'),

    }

    _zero_byte_params = [
        0x28, 0x29, 0x2e, 0x30, 0x31, 0x32, 0x4e, 0x51,
        0x52, 0x5d, 0x61, 0x62, 0x64, 0x65, 0x6c, 0x6f,
        0x73, 0x74, 0x75, 0x7d, 0x81, 0x85, 0x86, 0x87,
        0x88, 0x89, 0x8f, 0x90, 0x91, 0x92, 0x93, 0x94,
        0x97, 0x98,
    ]

    _readline_params = [
        0x46, 0x49, 0x4c, 0x50, 0x53, 0x56, 0x63, 0x67,
        0x69, 0x70,
    ]

    _simple_params = [
        0x47, 0x4a, 0x4b, 0x4d, 0x55, 0x68, 0x6a, 0x71,
        0x72, 0x80, 0x82, 0x83, 0x84, 0x95,
    ]

    _length_params = [
        0x42, 0x43, 0x54, 0x58, 0x8a, 0x8b, 0x8c, 0x8d,
        0x8e, 0x96,
    ]

    @staticmethod
    def alias(val):
        return PklOp._mapping_dict[val]['alias']

    @staticmethod
    def pbytes(val):
        return PklOp._mapping_dict[val]['pbytes']

    @staticmethod
    def lbytes(val):
        return PklOp._mapping_dict[val]['lbytes']

    @staticmethod
    def fmt(val):
        return PklOp._mapping_dict[val]['fmt']

    @staticmethod
    def is_readline(val):
        return val in PklOp._readline_params

    @staticmethod
    def no_params(val):
        return val in PklOp._zero_byte_params

    @staticmethod
    def is_simple(val):
        return val in PklOp._simple_params

    @staticmethod
    def has_length(val):
        return val in PklOp._length_params

    def __init__(self, opcode, param = None, byte_len = 0):
        self.opcode = opcode
        self.alias = PklOp.alias(opcode)
        self.pbytes = PklOp.pbytes(opcode)
        self.lbytes = PklOp.lbytes(opcode)
        self.fmt = PklOp.fmt(opcode)
        self.byte_len = 0
        self.param = param
        self.param2 = None # for GLOBAL

    def __repr__(self) -> str:
        if self.param and self.param2:
            return f"{self.alias}({self.param, self.param2})"
        elif self.param:
            return f"{self.alias}({self.param})"
        return f"{self.alias}()"
    
class PickleParsingReadlineParam(PickleParsingState):
    def parse_data(self, context: PObjParser):
        op = context.pickle_entry
        data = context.buffer.peek(0x4000)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse readline delimited pickle opcode")
        
        # Do we have a newline?
        # TODO: We *should* be more tolerant of very large parameters here.
        offset = data.find(b'\n')
        if offset == -1:
            raise EndOfDataException("Not enough data to find end of readline delimited pickle opcode")

        if op.opcode == PklOp.GLOBAL and op.param != None:
            op.param2 = data[0:offset+1]
            context.buffer.read(offset+1)
            context._next_state(PickleParsingOpCode)
            return

        op.param = data[0:offset+1]
        context.buffer.read(offset+1)
        if op.opcode == PklOp.GLOBAL:
            return
        context._next_state(PickleParsingOpCode)

class PickleParsingSimpleParam(PickleParsingState):
    def parse_data(self, context: PObjParser):
        op = context.pickle_entry
        data = context.buffer.peek(op.pbytes)
        if len(data) < op.pbytes:
            raise EndOfDataException("Not enough data to parse simple pickle opcode")

        op.param = struct.unpack(op.fmt, data)[0]
        context.buffer.read(op.pbytes)
        context._next_state(PickleParsingOpCode)

class PickleParsingLengthParam(PickleParsingState):
    def parse_data(self, context: PObjParser):
        op = context.pickle_entry
        data = context.buffer.peek(op.byte_len)
        if len(data) < op.byte_len:
            raise EndOfDataException("Not enough data to parse simple pickle opcode")

        op.param = data[0:op.byte_len]
        context.buffer.read(op.byte_len)
        context._next_state(PickleParsingOpCode)

class PickleParsingLengthPrefix(PickleParsingState):
    def parse_data(self, context: PObjParser):
        op = context.pickle_entry
        data = context.buffer.peek(op.lbytes)
        if len(data) < op.lbytes:
            raise EndOfDataException("Not enough data to parse simple pickle opcode")

        op.byte_len = struct.unpack(op.fmt, data[0:op.lbytes])[0]
        context.buffer.read(op.lbytes)
        context._next_state(PickleParsingLengthParam)

class PickleParsingOpCode(PickleParsingState):
    def parse_data(self, context: PObjParser):
        data = context.buffer.read(1)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse pickle opcode")
        
        # Note: We know that pytorch pickle is multiple pickles, but until
        #       we know why we care, we'll treat it as one.
        # TODO: Consider using STOP as a marker for pickle buffer children

        if PklOp.no_params(data[0]):
            context.pickle_list.append(PklOp(data[0]))
            return

        elif PklOp.is_simple(data[0]):
            context.pickle_entry = PklOp(data[0])
            context.pickle_list.append(context.pickle_entry)
            context._next_state(PickleParsingSimpleParam)
            return

        elif PklOp.has_length(data[0]):
            context.pickle_entry = PklOp(data[0])
            context.pickle_list.append(context.pickle_entry)
            context._next_state(PickleParsingLengthPrefix)
            return

        elif PklOp.is_readline(data[0]):
            context.pickle_entry = PklOp(data[0])
            context.pickle_list.append(context.pickle_entry)
            context._next_state(PickleParsingLengthParam)
            return

        raise UnsupportedFormatException(f"Invalid pickle opcode: {hex(data[0])}")

class Parser():
    # match_extenion
    # match_magic

    def __init__(self, parent: PObjBuffer, id:str):
        super().__init__(parent, id)
        self.state = PickleParsingOpCode()
        self.pickle_list = []
        self.meta['pickle_list'] = self.pickle_list
        self.pickle_entry = None

    def _next_state(self, state):
        self.state = state

    # scan_data        
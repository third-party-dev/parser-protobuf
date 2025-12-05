#!/usr/bin/env python3

import logging
log = logging.getLogger(__name__)

def ins_def(alias, lbytes=0, pbytes=0, fmt='', cast=None):
    return {
        'alias': alias,
        'lbytes': lbytes,
        'pbytes': pbytes,
        'fmt': fmt,
    }

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
    TUPLE3 = 135
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

    _mapping_dict = {
        # alias
        # lbytes - size of length prefix
        # pbytes - size of parameter
        # fmt - everything is little endian if not READLINE
        #   - if 'R', its readline, otherwise its the struct.unpack fmt

        0x28: ins_def("MARK"),
        0x29: ins_def("EMPTY_TUPLE"),
        0x2e: ins_def("STOP"),
        0x30: ins_def("POP"),
        0x31: ins_def("POP_MARK"),
        0x32: ins_def("DUP"),
        0x4e: ins_def("NONE"),
        0x51: ins_def("BINPERSID"),
        0x52: ins_def("REDUCE"),
        0x5d: ins_def("EMPTY_LIST"),
        0x61: ins_def("APPEND"),
        0x62: ins_def("BUILD"),
        0x64: ins_def("DICT"),
        0x65: ins_def("APPENDS"),
        0x6c: ins_def("LIST"),
        0x6f: ins_def("OBJ"),
        0x73: ins_def("SETITEM"),
        0x74: ins_def("TUPLE"),
        0x75: ins_def("SETITEMS"),
        0x7d: ins_def("EMPTY_DICT"),
        0x81: ins_def("NEWOBJ"),
        0x85: ins_def("TUPLE1"),
        0x86: ins_def("TUPLE2"),
        0x87: ins_def("TUPLE3"),
        0x88: ins_def("NEWTRUE"),
        0x89: ins_def("NEWFALSE"),
        0x8f: ins_def("EMPTY_SET"),
        0x90: ins_def("ADDITEMS"),
        0x91: ins_def("FROZENSET"),
        0x92: ins_def("NEWOBJ_EX"),
        0x93: ins_def("STACK_GLOBAL"),
        # ! TODO: SIZE?
        0x94: ins_def("MEMOIZE"),
        0x97: ins_def("NEXT_BUFFER"),
        0x98: ins_def("READONLY_BUFFER"),

        # Readline delimited
        0x46: ins_def("FLOAT", fmt='R'),
        0x49: ins_def("INT", fmt='R'),
        0x4c: ins_def("LONG", fmt='R'),
        0x50: ins_def("PERSID", fmt='R'),
        0x53: ins_def("STRING", fmt='R'),
        0x56: ins_def("UNICODE", fmt='R'),
        0x63: ins_def("GLOBAL", fmt='R'),
        0x67: ins_def("GET", fmt='R'),
        0x69: ins_def("INST", fmt='R'),
        0x70: ins_def("PUT", fmt='R'),

        # Static Sized Params
        0x47: ins_def("BINFLOAT", pbytes=8, fmt='<d'),
        0x4a: ins_def("BININT", pbytes=4, fmt='<i'),
        0x4b: ins_def("BININT1", pbytes=1, fmt='b'),
        0x4d: ins_def("BININT2", pbytes=2, fmt='<h'),
        0x55: ins_def("SHORT_BINSTRING", lbytes=1, fmt='B'),
        0x68: ins_def("BINGET", pbytes=1, fmt='B'),
        0x6a: ins_def("LONG_BINGET", pbytes=4, fmt='<i'),
        0x71: ins_def("BINPUT", pbytes=1, fmt='B'),
        0x72: ins_def("LONG_BINPUT", pbytes=4, fmt='<i'),
        0x80: ins_def("PROTO", pbytes=1, fmt='B'),
        0x82: ins_def("EXT1", pbytes=1, fmt='B'),
        0x83: ins_def("EXT2", pbytes=2, fmt='<h'),
        0x84: ins_def("EXT4", pbytes=4, fmt='<i'),
        0x95: ins_def("FRAME", pbytes=8, fmt='<q'),

        # Length Prefixed Params
        0x42: ins_def("BINBYTES", lbytes=4, fmt='<i'),
        0x43: ins_def("SHORT_BINBYTES", lbytes=1, fmt='B'),
        0x54: ins_def("BINSTRING", lbytes=4, fmt='<i'),
        0x58: ins_def("BINUNICODE", lbytes=4, fmt='<i'),
        0x8a: ins_def("LONG1", lbytes=1, fmt='B'),
        0x8b: ins_def("LONG4", lbytes=4, fmt='<i'),
        0x8c: ins_def("SHORT_BINUNICODE", lbytes=1, fmt='B'),
        0x8d: ins_def("BINUNICODE8", lbytes=8, fmt='<q'),
        0x8e: ins_def("BINBYTES8", lbytes=8, fmt='<q'),
        0x96: ins_def("BYTEARRAY8", lbytes=8, fmt='<q'),

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

    def __init__(self, opcode, param = None, byte_len = 0, byte_offset = None):
        self.opcode = opcode
        self.alias = PklOp.alias(opcode)
        self.pbytes = PklOp.pbytes(opcode)
        self.lbytes = PklOp.lbytes(opcode)
        self.fmt = PklOp.fmt(opcode)
        self.byte_len = 0
        self.param = param
        self.param2 = None # for GLOBAL

        self.byte_offset = byte_offset

    def __repr__(self) -> str:
        if self.param is not None and self.param2 is not None:
            return f"{self.alias}({self.param, self.param2})"
        elif self.param is not None:
            return f"{self.alias}({self.param})"
        return f"{self.alias}()"
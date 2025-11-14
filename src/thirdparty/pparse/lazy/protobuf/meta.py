#!/usr/bin/env python3

from google.protobuf import descriptor_pb2


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


class Field():
    # From: google/protobuf/descriptor.proto (FieldDescriptorProto)
    TYPE_DOUBLE = 1
    TYPE_FLOAT = 2
    TYPE_INT64 = 3
    TYPE_UINT64 = 4
    TYPE_INT32 = 5
    TYPE_FIXED64 = 6
    TYPE_FIXED32 = 7
    TYPE_BOOL = 8
    TYPE_STRING = 9
    TYPE_GROUP = 10
    TYPE_MESSAGE = 11
    TYPE_BYTES = 12
    TYPE_UINT32 = 13
    TYPE_ENUM = 14
    TYPE_SFIXED32 = 15
    TYPE_SFIXED64 = 16
    TYPE_SINT32 = 17
    TYPE_SINT64 = 18

    types = {
        1: "TYPE_DOUBLE",
        2: "TYPE_FLOAT",
        3: "TYPE_INT64",
        4: "TYPE_UINT64",
        5: "TYPE_INT32",
        6: "TYPE_FIXED64",
        7: "TYPE_FIXED32",
        8: "TYPE_BOOL",
        9: "TYPE_STRING",
        10: "TYPE_GROUP",
        11:	"TYPE_MESSAGE",
        12:	"TYPE_BYTES",
        13: "TYPE_UINT32",
        14:	"TYPE_ENUM",
        15: "TYPE_SFIXED32",
        16: "TYPE_SFIXED64",
        17: "TYPE_SINT32",
        18: "TYPE_SINT64",
    }
    
    LABEL_OPTIONAL = 1
    LABEL_REQUIRED = 2
    LABEL_REPEATED = 3

    labels = {
        1: "LABEL_OPTIONAL",
        2: "LABEL_REQUIRED",
        3: "LABEL_REPEATED",
    }

    def __init__(self, pbfield):
        self._pbfield = pbfield
        self.name = pbfield.name
        self.number = pbfield.number
        self.type = pbfield.type
        self.type_name = pbfield.type_name
        self.label = pbfield.label


    def type_str(self):
        return Field.types[self.type]


    def is_repeated(self):
        return self._pbfield.label == Field.LABEL_REPEATED


    def __repr__(self):
        return f"  Field: {self.name} #{self.number} : {self.type_str()}({self.type_name})"


class Msg(): 
    def __init__(self, pbmsg, pbfile):
        self.pbfile = pbfile
        self.pbmsg = pbmsg
        self.name = pbmsg.name
        self.type_name = f".{pbfile.package}.{pbmsg.name}"
        self._by_id = {}
        self._by_name = {}


    def add_field(self, pbfield):
        field = Field(pbfield)
        self._by_name[field.name] = field
        self._by_id[field.number] = field


    def by_name(self, name):
        return self._by_name[name]


    def by_id(self, id):
        return self._by_id[id]


    def __repr__(self):
        out = [f"MsgType: {self.type_name}"]
        for field in self._by_name.values():
            out.append(f"{field}")
        return '\n'.join(out)


class OnnxPb():
    def __init__(self):
        with open("proto/onnx.pb", "rb") as f:
            pbset = descriptor_pb2.FileDescriptorSet()
            pbset.ParseFromString(f.read())

        # Re-index to something that makes sense to me.
        db = {}
        for pbmsg in pbset.file[0].message_type:
            msg = Msg(pbmsg, pbset.file[0])
            db[msg.type_name] = msg
            for field in pbmsg.field:
                msg.add_field(field)        

        self.db = db


    def by_type_name(self, type_name):
        return self.db[type_name]


#print(db['.onnx.ModelProto'])

'''
stack up message types with current tracked as len(types)
'''
#!/usr/bin/env python3

from google.protobuf import descriptor_pb2

class Field():
    def __init__(self, pbfield):
        self._pbfield = pbfield
        self.name = pbfield.name
        self.number = pbfield.number
        self.type = pbfield.type
        self.type_name = pbfield.type_name


    def type_str(self):
        types = {
            1: "TYPE_DOUBLE",
            2: "TYPE_FLOAT",
            3: "TYPE_INT64",
            4: "TYPE_UINT64",
            5: "TYPE_INT32",
            8: "TYPE_BOOL",
            9: "TYPE_STRING",
            11:	"TYPE_MESSAGE",
            12:	"TYPE_BYTES",
            14:	"TYPE_ENUM",
        }
        return types[self.type]


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
        with open("onnx.pb", "rb") as f:
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
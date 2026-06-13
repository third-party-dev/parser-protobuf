#!/usr/bin/env python3

from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger(__name__)

from google.protobuf import descriptor_pb2


class Field:
    # From: google/protobuf/descriptor.proto (FieldDescriptorProto)
    TYPE_DOUBLE: int = 1
    TYPE_FLOAT: int = 2
    TYPE_INT64: int = 3
    TYPE_UINT64: int = 4
    TYPE_INT32: int = 5
    TYPE_FIXED64: int = 6
    TYPE_FIXED32: int = 7
    TYPE_BOOL: int = 8
    TYPE_STRING: int = 9
    TYPE_GROUP: int = 10
    TYPE_MESSAGE: int = 11
    TYPE_BYTES: int = 12
    TYPE_UINT32: int = 13
    TYPE_ENUM: int = 14
    TYPE_SFIXED32: int = 15
    TYPE_SFIXED64: int = 16
    TYPE_SINT32: int = 17
    TYPE_SINT64: int = 18

    types: dict[int, str] = {
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
        11: "TYPE_MESSAGE",
        12: "TYPE_BYTES",
        13: "TYPE_UINT32",
        14: "TYPE_ENUM",
        15: "TYPE_SFIXED32",
        16: "TYPE_SFIXED64",
        17: "TYPE_SINT32",
        18: "TYPE_SINT64",
    }

    LABEL_OPTIONAL: int = 1
    LABEL_REQUIRED: int = 2
    LABEL_REPEATED: int = 3

    labels: dict[int, str] = {
        1: "LABEL_OPTIONAL",
        2: "LABEL_REQUIRED",
        3: "LABEL_REPEATED",
    }


    def __init__(self, pbfield: Any) -> None:
        self._pbfield: Any = pbfield
        self.name: str = pbfield.name
        self.number: int = pbfield.number
        self.type: int = pbfield.type
        self.type_name: str = pbfield.type_name
        self.label: int = pbfield.label


    def type_str(self) -> str:
        return Field.types[self.type]


    def is_repeated(self) -> bool:
        return self._pbfield.label == Field.LABEL_REPEATED


    def __repr__(self) -> str:
        return f"  Field: {self.name} #{self.number} : {self.type_str()}({self.type_name})"


class Protobuf:
    VARINT: int = 0
    I64: int = 1
    LEN: int = 2
    SGROUP: int = 3
    EGROUP: int = 4
    I32: int = 5

    FALSE: int = 0
    TRUE: int = 1

    wire_type_str: dict[int, str] = {
        0: "VARINT",
        1: "I64",
        2: "LEN",
        3: "SGROUP",
        4: "EGROUP",
        5: "I32",
    }

    inline_types: list[int] = [
        Field.TYPE_INT64,
        Field.TYPE_INT32,
        Field.TYPE_UINT64,
        Field.TYPE_UINT32,
        Field.TYPE_BOOL,
        Field.TYPE_ENUM,
    ]


class Msg:


    def __init__(self, pbmsg: Any, prefix: str) -> None:
        self.pbmsg: Any = pbmsg
        self.name: str = pbmsg.name
        self._type_name: str = f"{prefix}.{pbmsg.name}"
        self._by_id: dict[int, Field] = {}
        self._by_name: dict[str, Field] = {}


    def type_name(self) -> str:
        return self._type_name


    def add_field(self, pbfield: Any) -> None:
        field = Field(pbfield)
        self._by_name[field.name] = field
        self._by_id[field.number] = field


    def by_name(self, name: str) -> Field:
        return self._by_name[name]


    def by_id(self, id: int) -> Field:
        return self._by_id[id]


    def __repr__(self) -> str:
        out = [f"MsgType: {self._type_name}"]
        for field in self._by_name.values():
            out.append(f"{field}")
        return "\n".join(out)


class PbImport:


    def __init__(self, pbpath: Optional[Any] = None) -> None:
        self.pbpath: Optional[Any] = pbpath
        self.db: dict[str, Msg] = {}
        self.process_pb2()


    def process_descriptor_proto(self, pbmsgtypes: Any, prefix: str) -> None:
        if self.pbpath is None:
            # TODO: OK to silently fail?
            return

        for pbmsg in pbmsgtypes:
            msg = Msg(pbmsg, prefix)
            self.db[msg.type_name()] = msg
            for field in pbmsg.field:
                msg.add_field(field)
            self.process_descriptor_proto(pbmsg.nested_type, msg.type_name())


    def process_pb2(self) -> None:
        if self.pbpath is None:
            # TODO: OK to silently fail?
            return

        # protoc --proto_path=. --descriptor_set_out=onnx.pb --include_imports onnx.proto3
        with open(self.pbpath, "rb") as f:
            pbset = descriptor_pb2.FileDescriptorSet()
            pbset.ParseFromString(f.read())

        # Re-index to something that makes sense to me.
        self.db = {}
        prefix = f".{pbset.file[0].package}"
        pbmsgtypes = pbset.file[0].message_type
        self.process_descriptor_proto(pbmsgtypes, prefix)


    def by_type_name(self, type_name: str) -> Msg:
        if self.pbpath is None:
            # TODO: This should be a ValueError?
            raise NotImplementedError()

        return self.db[type_name]

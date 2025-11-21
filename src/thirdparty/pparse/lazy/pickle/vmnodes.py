#!/usr/bin/env python3

#from thirdparty.pparse.lazy.protobuf import ProtobufParsingState, ProtobufParsingKey
import thirdparty.pparse.lib as pparse


def trace(*args, **kwargs):
    print(*args, **kwargs)
    pass


class NodeVmContext(pparse.NodeContext):
    def __init__(self, node: 'Node', parent: 'Node', reader: pparse.Range):
        if type(reader).__name__ != 'Range':
            raise Exception("protobuf NodeContext reader must be a pparse.Range")

        super().__init__(node, parent, reader)
        self._vmstate = None
        if not isinstance(node, NodeVmState):
            self._vmstate = parent.ctx().vmstate()

    def vmstate(self):
        return self._vmstate


class Node(pparse.Node):
    # Note: All Protobuf readers are Ranges. Range is required to process protobuf. 
    def __init__(self, parent: 'Node', reader: pparse.Range):
        if type(reader).__name__ != 'Range':
            raise Exception("pickle Node reader must be a pparse.Range")
        super().__init__(parent, reader, NodeVmContext(self, parent, reader.dup()))


class NodeVmState(Node):
    def __init__(self, parent: Node, reader: pparse.Reader):
        super().__init__(parent, reader)
        self.memo = {}
        self.proto = None


class NodeList(Node):
    def __init__(self, parent: Node, reader: pparse.Reader):
        super().__init__(parent, reader)
        self.value = []


class NodeObject(Node):
    def __init__(self, parent: Node, reader: pparse.Reader):
        super().__init__(parent, reader)


class NodeImport(Node):
    def __init__(self, parent: Node, reader: pparse.Reader):
        super().__init__(parent, reader)
        

class NodeTuple(Node):
    def __init__(self, parent: Node, reader: pparse.Reader):
        super().__init__(parent, reader)


class NodeExternal(Node):
    def __init__(self, parent: Node, reader: pparse.Reader):
        super().__init__(parent, reader)


class NodeCall(Node):
    def __init__(self, parent: Node, reader: pparse.Reader):
        super().__init__(parent, reader)




# class NodeMap(Node):
#     def __init__(self, parent: Node, reader: pparse.Reader):
#         super().__init__(parent, reader)
#         self.value = {}


#     def dumps(self, depth=0, step=2):
#         spacer = ' ' * depth
#         proto_type = self.msgtype().name
#         result = [f'{spacer}<PickleMapNode type="{proto_type}" offset="{self.tell()}">' "{"]
#         for k,v in self.value.items():
#             if isinstance(v, Node):
#                 result.append(f"{spacer}{' '*step}{k}:")
#                 result.append(f"{v.dumps(depth+(step*2))}")
#             else:
#                 v_str = f"{v}"
#                 if len(v_str) < 40:
#                     result.append(f"{spacer}{' '*step}{k}: {v}")
#         result.append(f"{spacer}" "}</PickleMapNode>")
#         return '\n'.join(result)

#     def __repr__(self):
#         # Designed for usage in breakpoint()s and REPLs
#         py_type = "NodeMap"
#         msg_type = "UNKNOWN"
#         if self._type:
#             msg_type = self._type.name
#         val_type = type(self.value).__name__
#         name = ''
#         if self.value and 'name' in self.value:
#             name = f'name={self.value["name"]}, '
#         return f"{py_type}(_type={msg_type}, {name}value={val_type})"


# class NodeArray(Node):
#     def __init__(self, parent: Node, reader: pparse.Reader, protobuf_type):
#         super().__init__(parent, reader, protobuf_type)
#         self.value = []


#     def dumps(self, depth=0, step=2):
#         spacer = ' ' * depth
#         proto_type = self.msgtype().name
#         result = [f'{spacer}<ProtobufArrayNode type="{proto_type}" offset="{self.tell()}">[']
#         for e in self.value:
#             if isinstance(e, Node):
#                 result.append(f"{e.dumps(depth+step)}")
#             else:
#                 result.append(f"{spacer}{' '*step}{e}")
#         result.append(f"{spacer}]</ProtobufArrayNode>")
#         return '\n'.join(result)

#     def __repr__(self):
#         # Designed for usage in breakpoint()s and REPLs
#         py_type = "NodeArray"
#         msg_type = "UNKNOWN"
#         if self._type:
#             msg_type = self._type.name
#         val_type = type(self.value).__name__
#         return f"{py_type}(_type={msg_type}, value={val_type})"
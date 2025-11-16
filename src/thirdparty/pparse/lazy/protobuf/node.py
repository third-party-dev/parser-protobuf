#!/usr/bin/env python3

#from thirdparty.pparse.lazy.protobuf import ProtobufParsingState, ProtobufParsingKey
from thirdparty.pparse.lib import NodeContext as BaseNodeContext
import thirdparty.pparse.lib as pparse

from thirdparty.pparse.lib import (
    EndOfDataException,
    UnsupportedFormatException,
    EndOfNodeException
)


class UnloadedValue():
    def __repr__(self): return "<UNLOADED_VALUE />"
UNLOADED_VALUE = UnloadedValue()


class NodeContext(BaseNodeContext):
    def __init__(self, node: 'Node', parent: 'Node', state: 'ProtobufParsingState', reader: pparse.Reader):
        super().__init__(node, parent, state, reader)
        self._key = None
        # self._key_wire_type = None
        # self._key_field_num = None
        # self._key_length = None
        # self._key_field = None


    def key(self):
        return self._key


    def set_key(self, field): #wire_type, field_num, key_length, field):
        #     'start': 
        #     'wire_type': None,
        #     'field_num': None,
        #     'length': None,
        #     'field': None,
        # }
        # self._key_start = self.tell()
        # self._key_wire_type = wire_type
        # self._key_field_num = field_num
        # self._key_length = key_length
        # self._key_field = field
        self._key = field


class Node():
    def __init__(self, parent: 'Node', reader: pparse.Reader, protobuf_type):
        from thirdparty.pparse.lazy.protobuf import ProtobufParsingKey
        self._type = protobuf_type
        self._reader : Reader = reader.dup()        
        self.value = UNLOADED_VALUE
        self._ctx = NodeContext(self, parent, ProtobufParsingKey(), reader.dup())


    def field_by_id(self, field_num):
        return self._type.by_id(field_num)

    
    def ctx(self):
        return self._ctx


    def clear_ctx(self):
        self._ctx = None
        return self


    def tell(self):
        return self._reader.tell()


    def final_length(self, length):
        self._reader = pparse.Range(self._reader.dup(), length)
        return self


    def length(self):
        return self._reader.length()


    def msgtype(self):
        return self._type


    # Assumed that this method is not run until after the Extraction parsing is complete.
    def load(self, parser):
        from thirdparty.pparse.lazy.protobuf import ProtobufParsingKey
        # Create a headless node to parse the data.
        self._ctx = NodeContext(self, None, ProtobufParsingKey(), self._reader.dup())
        # Reset to beginning of field.
        self._ctx.seek(0)

        parser.current = self
        # While not end of data, keep parsing via states.
        try:
            while True:
                ctx = parser.current.ctx()
                state = ctx.state()
                # if isinstance(state, ProtobufParsingString):
                #     breakpoint()
                state.parse_data(parser, ctx)
        except EndOfNodeException as e:
            pass
        except EndOfDataException as e:
            pass
        except UnsupportedFormatException:
            raise

    
    def unload(self):
        self.value = UNLOADED_VALUE


    def dumps(self, depth=0, step=2):
        spacer = ' ' * depth
        result = [f"{spacer}" f'<ProtobufNode length="{self.length()}" offset="{self.tell()}">']
        if isinstance(self.value, Node):
            result.append(f"{spacer}{self.value.dumps(depth+step)}")
        else:
            result.append(f"{spacer}{' '*step}{self.value}")
        result.append(f"{spacer}</ProtobufNode>")
        return '\n'.join(result)


    def __repr__(self):
        # Designed for usage in breakpoint()s and REPLs
        py_type = "Node"
        msg_type = "UNKNOWN"
        if self._type:
            msg_type = self._type.name
        val_type = type(self.value).__name__
        return f"{py_type}(_type={msg_type}, value={val_type})"



# class NodeInit(Node):
#     def __init__(self, parent: Node, reader: pparse.Reader, parser: pparse.Parser = None):
#         super().__init__(parent, reader)

#         # Since there is only 1 NodeInit, we can keep more stuff here.
#         self.parser = parser

    
#     def dumps(self, depth=0, step=2):
#         spacer = ' ' * depth
#         #result = [f"{spacer}" f'<NodeInit length="{self.length()}">']
#         result = [f"{spacer}" f'<ProtobufNodeInit>']
#         if isinstance(self.value, Node):
#             result.append(f"{spacer}{self.value.dumps(depth+step)}")
#         else:
#             result.append(f"{spacer}{self.value}")
#         result.append(f"{spacer}</ProtobufNodeInit>")
#         return '\n'.join(result)


class NodeMap(Node):
    def __init__(self, parent: Node, reader: pparse.Reader, protobuf_type):
        super().__init__(parent, reader, protobuf_type)
        self.value = {}


    def dumps(self, depth=0, step=2):
        spacer = ' ' * depth
        proto_type = protobuf_type.name
        result = [f'{spacer}<ProtobufMapNode type="{proto_type}" length="{self.length()}" offset="{self.tell()}">' "{"]
        for k,v in self.value.items():
            if isinstance(v, Node):
                result.append(f"{spacer}{' '*step}{k}:")
                result.append(f"{v.dumps(depth+(step*2))}")
            else:
                result.append(f"{spacer}{' '*step}{k}: {v}")
        result.append(f"{spacer}" "}</ProtobufMapNode>")
        return '\n'.join(result)

    def __repr__(self):
        # Designed for usage in breakpoint()s and REPLs
        py_type = "NodeMap"
        msg_type = "UNKNOWN"
        if self._type:
            msg_type = self._type.name
        val_type = type(self.value).__name__
        return f"{py_type}(_type={msg_type}, value={val_type})"


class NodeArray(Node):
    def __init__(self, parent: Node, reader: pparse.Reader, protobuf_type):
        super().__init__(parent, reader, protobuf_type)
        self.value = []


    def dumps(self, depth=0, step=2):
        spacer = ' ' * depth
        proto_type = protobuf_type.name
        result = [f'{spacer}<ProtobufArrayNode type="{proto_type}" length="{self.length()}" offset="{self.tell()}">[']
        for e in self.value:
            if isinstance(e, Node):
                result.append(f"{spacer}{e.dumps(depth+step)}")
            else:
                result.append(f"{spacer}{' '*step}{e}")
        result.append(f"{spacer}]</ProtobufArrayNode>")
        return '\n'.join(result)

    def __repr__(self):
        # Designed for usage in breakpoint()s and REPLs
        py_type = "NodeArray"
        msg_type = "UNKNOWN"
        if self._type:
            msg_type = self._type.name
        val_type = type(self.value).__name__
        return f"{py_type}(_type={msg_type}, value={val_type})"


#!/usr/bin/env python3

from thirdparty.pparse.lazy.json.state import JsonParsingState, JsonParsingStart
from thirdparty.pparse.lib import NodeContext as BaseNodeContext
from thirdparty.pparse import lib as pparse

from thirdparty.pparse.lib import (
    EndOfDataException,
    UnsupportedFormatException,
    EndOfNodeException
)


class UnloadedValue():
    def __repr__(self): return "<UNLOADED_VALUE />"
UNLOADED_VALUE = UnloadedValue()


class NodeContext(BaseNodeContext):
    def __init__(self, node: 'Node', parent: 'Node', state: JsonParsingState, reader: pparse.Reader):
        super().__init__(node, parent, state, reader)
        self._key_reg = None


    def key(self):
        return self._key_reg


    def set_key(self, v):
        self._key_reg = v
        return self


class Node():
    def __init__(self, parent: 'Node', reader: pparse.Reader):
        self._reader : Reader = reader.dup()        
        self.value = UNLOADED_VALUE
        self._ctx = NodeContext(self, parent, JsonParsingStart(), reader.dup())

    
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


    # Assumed that this method is not run until after the Extraction parsing is complete.
    def load(self, parser):
        # Create a headless node to parse the data.
        self._ctx = NodeContext(self, None, JsonParsingStart(), self._reader.dup())
        # Reset to beginning of field.
        self._ctx.seek(0)

        parser.current = self
        # While not end of data, keep parsing via states.
        try:
            while True:
                ctx = parser.current.ctx()
                state = ctx.state()
                # if isinstance(state, JsonParsingString):
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


    # NOT WORKING
    def dumps(self, depth=0, step=2):
        spacer = ' ' * depth
        result = [f"{spacer}" f'<Node length="{self.length()}" offset="{self.tell()}">']
        if isinstance(self.value, Node):
            result.append(f"{spacer}{self.value.dumps(depth+step)}")
        else:
            result.append(f"{spacer}{' '*step}{self.value}")
        result.append(f"{spacer}</Node>")
        return '\n'.join(result)


    # YUCK
    def __repr__(self):
        result = ["<NodeInit>"]
        result.append(f"  {self.value}")
        result.append("</NodeInit>")
        return '\n'.join(result)


class NodeInit(Node):
    def __init__(self, parent: Node, reader: pparse.Reader, parser: pparse.Parser = None):
        super().__init__(parent, reader)

        # Since there is only 1 NodeInit, we can keep more stuff here.
        self.parser = parser

    
    def dumps(self, depth=0, step=2):
        spacer = ' ' * depth
        #result = [f"{spacer}" f'<NodeInit length="{self.length()}">']
        result = [f"{spacer}" f'<NodeInit>']
        if isinstance(self.value, Node):
            result.append(f"{spacer}{self.value.dumps(depth+step)}")
        else:
            result.append(f"{spacer}{self.value}")
        result.append(f"{spacer}</NodeInit>")
        return '\n'.join(result)


class NodeMap(Node):
    def __init__(self, parent: Node, reader: pparse.Reader):
        super().__init__(parent, reader)
        self.value = {}


    # NOT WORKING
    def dumps(self, depth=0, step=2):
        spacer = ' ' * depth
        result = [f'{spacer}<NodeMap length="{self.length()}" offset="{self.tell()}">' "{"]
        for k,v in self.value.items():
            if isinstance(v, Node):
                result.append(f"{spacer}{' '*step}{k}:")
                result.append(f"{v.dumps(depth+(step*2))}")
            else:
                result.append(f"{spacer}{' '*step}{k}: {v}")
        result.append(f"{spacer}" "}</NodeMap>")
        return '\n'.join(result)


    # YUCK
    def __repr__(self):
        result = ["<NodeMap>{"]
        for k,v in self.value.items():
            result.append(f"  {k}: {v}")
        result.append("}</NodeMap>")
        return '\n'.join(result)


class NodeArray(Node):
    def __init__(self, parent: Node, reader: pparse.Reader):
        super().__init__(parent, reader)
        self.value = []


    # NOT WORKING
    def dumps(self, depth=0, step=2):
        spacer = ' ' * depth
        result = [f'{spacer}<NodeArray length="{self.length()}" offset="{self.tell()}">[']
        for e in self.value:
            if isinstance(e, Node):
                result.append(f"{spacer}{e.dumps(depth+step)}")
            else:
                result.append(f"{spacer}{' '*step}{e}")
        result.append(f"{spacer}]</NodeArray>")
        return '\n'.join(result)


    # YUCK
    def __repr__(self):
        result = ["<NodeArray>["]
        for e in self.value:
            result.append(f"  {e}")
        result.append("]</NodeArray>")
        return '\n'.join(result)
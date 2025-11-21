#!/usr/bin/env python3

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lib import NodeContext as BaseNodeContext


class NodeContext(BaseNodeContext):
    def __init__(self, node: 'Node', parent: 'Node', reader: pparse.Reader):
        super().__init__(node, parent, reader)

    def left(self):
        return self._reader.left()


# For Zipfiles, Node will track the compressed data sections. The decompressed
# data will be tracked as an Extraction that can be tracked in the node and the
# parser's source Extraction.
class Node():
    def __init__(self, parent: 'Node', reader: pparse.Reader):
        self._reader : Reader = reader.dup()  
        self.value = pparse.UNLOADED_VALUE
        self._ctx = NodeContext(self, parent, reader.dup(), )

    
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
    # def load(self, parser):
    #     # Create a headless node to parse the data.
    #     self._ctx = NodeContext(self, None, JsonParsingStart(), self._reader.dup())
    #     # Reset to beginning of field.
    #     self._ctx.seek(0)

    #     parser.current = self
    #     # While not end of data, keep parsing via states.
    #     try:
    #         while True:
    #             ctx = parser.current.ctx()
    #             state = ctx.state()
    #             # if isinstance(state, JsonParsingString):
    #             #     breakpoint()
    #             state.parse_data(parser, ctx)
    #     except paprse.EndOfNodeException as e:
    #         pass
    #     except pparse.EndOfDataException as e:
    #         pass
    #     except pparse.UnsupportedFormatException:
    #         raise

    
    def unload(self):
        self.value = pparse.UNLOADED_VALUE


    # def dumps(self, depth=0, step=2):
    #     spacer = ' ' * depth
    #     result = [f"{spacer}" f'<JsonNode length="{self.length()}" offset="{self.tell()}">']
    #     if isinstance(self.value, Node):
    #         result.append(f"{spacer}{self.value.dumps(depth+step)}")
    #     else:
    #         result.append(f"{spacer}{' '*step}{self.value}")
    #     result.append(f"{spacer}</JsonNode>")
    #     return '\n'.join(result)


class NodeMap(Node):
    def __init__(self, parent: Node, reader: pparse.Reader):
        super().__init__(parent, reader)
        self.value = {}


    def dumps(self, depth=0, step=2):
        spacer = ' ' * depth
        result = [f'{spacer}<ZipMapNode length="{self.length()}" offset="{self.tell()}">' "{"]
        for k,v in self.value.items():
            if isinstance(v, Node):
                result.append(f"{spacer}{' '*step}{k}:")
                result.append(f"{v.dumps(depth+(step*2))}")
            else:
                result.append(f"{spacer}{' '*step}{k}: {v}")
        result.append(f"{spacer}" "}</ZipMapNode>")
        return '\n'.join(result)


class NodeArray(Node):
    def __init__(self, parent: Node, reader: pparse.Reader):
        super().__init__(parent, reader)
        self.value = []


    def dumps(self, depth=0, step=2):
        spacer = ' ' * depth
        result = [f'{spacer}<ZipArrayNode length="{self.length()}" offset="{self.tell()}">[']
        for e in self.value:
            if isinstance(e, Node):
                result.append(f"{spacer}{e.dumps(depth+step)}")
            else:
                result.append(f"{spacer}{' '*step}{e}")
        result.append(f"{spacer}]</ZipArrayNode>")
        return '\n'.join(result)

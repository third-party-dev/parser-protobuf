#!/usr/bin/env python3

#from thirdparty.pparse.lazy.protobuf import ProtobufParsingState, ProtobufParsingKey
import thirdparty.pparse.lib as pparse


def trace(*args, **kwargs):
    print(*args, **kwargs)
    pass


class NodeContext(pparse.NodeContext):
    def __init__(self, node: 'Node', parent: 'Node', reader: pparse.Range):
        if type(reader).__name__ != 'Range':
            raise Exception("protobuf NodeContext reader must be a pparse.Range")
        super().__init__(node, parent, reader)


class NodeVmContext(pparse.NodeContext):
    def __init__(self, node: 'Node', parent: 'Node', reader: pparse.Range):
        if type(reader).__name__ != 'Range':
            raise Exception("protobuf NodeContext reader must be a pparse.Range")
        super().__init__(node, parent, reader)

        self.stack = []
        self.memo = {}
        self.history = []
        self.current_op = None

    def vmstate(self):
        return self._vmstate


# An array of NodePickle objects.
class NodePickleArray(pparse.Node):
    def __init__(self, parent: pparse.Node, reader: pparse.Reader):
        super().__init__(parent, reader, NodeContext(self, parent, reader.dup()))
        self.value = []


class NodePickle(pparse.Node):
    '''
        A single pickle stream.
        There are 2 processes interlaced in the processing of a single pickle stream.
        - The parsing of the opcodes.
        - The interpretation of the opcodes into a node tree.

        Opcodes are parsed into a running stack.

        As opcodes (results) are consumed by other opcodes, they are relocated to
        the objects that have consumed them. In this way, we should be able to
        completely reconstruct the original listing by recursives traversing the
        final object node tree.
    '''
    def __init__(self, parent: pparse.Node, reader: pparse.Reader):
        super().__init__(parent, reader, NodeVmContext(self, parent, reader.dup()))
        
        self.proto = None
        self.value = []
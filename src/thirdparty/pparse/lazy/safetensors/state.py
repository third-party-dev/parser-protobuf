#!/usr/bin/env python3

from __future__ import annotations

import logging
import struct

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse

'''
    The Safetensors parsing process generally follows:
    - STATE: SafetensorsParsingLength
      - Get the 64bit (8 byte) little endian length as 'header_length'.
    - STATE: SafetensorsParsingHeaderSetup
      - Create a LazyJsonParser node as 'header'
      - Let Node.load() handle the JSON parse via ctx()._descendants
    - STATE: SafetensorsParsingTensorsMeta
      - Use the 'header' to build all the Tensor nodes
      - Each node is populated with the metadata
      - Each node given 'data' field with UNLOADED Node and 'SafetensorsParsingTensorNode' state.
        - The UNLOADED node is given context to load with 'SafetensorsParsingTensorNode' state.
      - _Tensor nodes are not implicitly parsed._
    - STATE: SafetensorsParsingTensorNode
      - When a Node.load() runs on a node with 'SafetensorsParsingTensorNode' state, it'll read the data into memory.
'''


class SafetensorsParsingState(object):
    def parse_data(self, node: pparse.Node) -> int:
        raise NotImplementedError()


class SafetensorsParsingComplete(SafetensorsParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        return pparse.ASCEND


class SafetensorsParsingTensorNode(SafetensorsParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        node._value = ctx.read(ctx.left())

        ctx._next_state(SafetensorsParsingComplete)
        return pparse.ASCEND


class SafetensorsParsingTensorsMeta(SafetensorsParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        # We only need the data reference, we seek(tensor_data_start) for each node.
        tensor_reader = ctx.reader()
        node._value['tensors'] = {}
        for k,v in node.value['header'].value.value.items():
            if k == '__metadata__':
                continue
            # Create UNLOADED nodes for each Tensor.
            node._value['tensors'][k] = parser.tensor_node_from(tensor_reader, node, k, v)

        # We're done.
        node.ctx()._next_state(SafetensorsParsingComplete)
        #breakpoint()
        return pparse.ASCEND

        # # Keep it going forward.
        # data = ctx.read(4096 * 4096)
        # if not data or len(data) < 1:
        #     ctx.node().tensor_data_end = ctx.tell()
        #     raise pparse.EndOfDataException("No more Safetensors tensor data.")


class SafetensorsParsingHeaderSetup(SafetensorsParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        #breakpoint()
        from thirdparty.pparse.lazy.json import configure_pparser
        json_parser = configure_pparser().from_reader(node.ctx().reader())

        node._value['header'] = json_parser.make_root_node(parent=node)
        # Let Node.load() handle it.
        node.ctx()._descendants.append(node._value['header'])

        # ! Assuming success. TODO: Node should be able to verify json parse success before continuing.
        ctx._next_state(SafetensorsParsingTensorsMeta)

        return pparse.AGAIN


class SafetensorsParsingLength(SafetensorsParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        data = ctx.peek(8)
        if len(data) < 8:
            raise EndOfDataException(
                "Not enough data to parse Safetensors Header Length"
            )

        header_length = struct.unpack("<Q", data)[0]
        node._value['header_length'] = header_length
        log.debug(f"Safetensors Header Length: {node._value['header_length']}")
        ctx.skip(8)

        ctx._next_state(SafetensorsParsingHeaderSetup)
        return pparse.AGAIN



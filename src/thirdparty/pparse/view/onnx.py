#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Iterator, Optional

import logging
import numpy

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.protobuf import configure_pparser
from thirdparty.pparse.lazy.onnx.meta import OnnxDataType

"""
  Bulk tensor data is stored in GraphProto.initializer = []
  Graph structure is stoed in GraphProto.node = []
"""


class Tensor(pparse.Tensor):


    def __init__(self, onnx_view: Onnx, init_node: pparse.Node, name: str) -> None:
        self._name = name
        self._view = onnx_view
        self._init_node = init_node


    def get_onnx_type(self) -> int:
        return self._init_node.value['data_type']


    # Return (safetensors equivalent) type
    def get_type(self) -> str:
        return OnnxDataType.sttype(self.get_onnx_type())


    # Return (safetensors equivalent) shape
    def get_shape(self) -> list[Any]:
        if 'dims' in self._init_node.value:
            shape = self._init_node.value['dims']
        else:
            # Assuming no dims means this is a constant
            # TODO: We can further verify its a "tensor" by looking for 'data_type', 'name', and 'raw_data'.
            shape = [1]
        return shape


    # Return raw data as extracted from source
    def get_data_bytes(self) -> Any:
        return self._init_node.value['raw_data'].value


    # Return raw data as python array of dtype
    def as_array(self) -> None:
        raise NotImplementedError()


    # Return raw data as numpy array of dtype
    def as_numpy(self) -> Any:
        dtype = OnnxDataType.nptype(self.get_onnx_type())

        arr = numpy.frombuffer(self.get_data_bytes(), dtype=dtype)

        if 'dims' in self._init_node.value:
            return arr.reshape(self.get_shape())
        return arr.reshape(())


class Onnx:


    def __init__(self) -> None:
        self._extraction: Optional[pparse.BytesExtraction] = None
        self._tensor_meta: dict[str, Tensor] = {}


    def _parse(self, data_source: Any, fname: str = "unnamed.onnx", recursion: Optional[pparse.RecursionControl] = None) -> Onnx:
        # from importlib import resources
        # data_path = resources.files("thirdparty.pparse.data")
        # proto = PbImport(data_path / "proto" / "onnx.pb")

        try:
            data_range = pparse.Range(data_source.open(), data_source.length)
            self._extraction = pparse.BytesExtraction(name=fname, reader=data_range)
            parser_class = configure_pparser(
                ext_list=[".onnx"],
                init_msgtype=".onnx.ModelProto",
                pkg_namespace="thirdparty.pparse.data",
                relative_path="proto/onnx.pb",
                #proto=proto
            )
            parser = parser_class(self._extraction, 'protobuf')

            self._extraction.add_result('protobuf', parser.make_root_node())
            self._extraction._result['protobuf'].load(recursion=recursion)

            #self._extraction.add_parser('protobuf', parser)
            #self._extraction.discover_parsers({"protobuf": parser})
            #self._extraction._parser['protobuf']._root.load(recursion=recursion)

            # Some light post processing.
            self.root = self._extraction._result["protobuf"]
            self.model = self.root.value
            self.graph = self.model["graph"].value
            self.nodes = self.graph["node"]
            self.initializers = self.graph["initializer"]

            for tnode in self.graph['initializer']:
                self._tensor_meta[tnode.value['name']] = Tensor(self, tnode, tnode.value['name'])

        except pparse.EndOfDataException as e:
            print(e)
            pass
        except Exception as e:
            print(e)
            import traceback

            traceback.print_exc()

        # ** New Development Of Graph Interface
        self.idx_nodes, self.idx_to_name = self.graph_nodes()

        return self


    def root_node(self) -> pparse.Node:
        return self._extraction._result['protobuf']


    def open_fpath(self, fpath: str, recursion: Optional[pparse.RecursionControl] = None) -> Onnx:
        return self._parse(pparse.FileData(path=fpath), fname=fpath, recursion=recursion)


    def from_bytesio(self, bytes_io: Any, fname: str = "unnamed.onnx", recursion: Optional[pparse.RecursionControl] = None) -> Onnx:
        return self._parse(pparse.BytesIoData(bytes_io=bytes_io), fname=fname, recursion=recursion)


    def tensor_names(self) -> list[str]:
        return list(self._tensor_meta.keys())


    def tensor(self, name: str) -> Tensor:
        return self._tensor_meta[name]


    def find_node(self, name: str) -> Optional[pparse.Node]:
        for node in self.nodes:
            if node.value["name"] == name:
                return node
        return None


    # ** ---- New Development Of Graph Interface ----
    def _collect_all_nodes(self, graph: Any) -> Iterator[Any]:
        for node in graph:
            #breakpoint()
            yield node._value
            if 'attribute' in node._value:
                for attr_node in node._value['attribute']:
                    if 'g' in attr_node._value:
                        yield from self._collect_all_nodes(attr_node._value['g'])
                    # repeated subgraphs (rare)
                    if 'graphs' in attr_node._value:
                        # ! untested
                        for subgraph in attr_node._value['graphs']:
                            yield from self._collect_all_nodes(subgraph)


    def collect_all_nodes(self) -> list[Any]:
        try:
            all_nodes = list(self._collect_all_nodes(self.root_node()._value['graph']._value['node']))
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)
            raise
        return all_nodes


    def graph_nodes(self) -> tuple[list[dict[str, Any]], dict[int, str]]:
        """graph_nodes
        """
        
        '''
            A list of nodes that describe inputs and outputs in a way that we can use to
            reconstruct the graph. Aside from inputs/outputs, it may also have names,
            operation, and other attributes.

            TODO: Normalize this notion.
            - Without operation names, we can generate based on existing attributes.
            - Without node name, we can generate based on path and existing attributes.

            Maybe all graphs need to be generalized into a list of nodes where:
            - inputs are a list of indicies
            - outputs are a list of indicies
            - index is the self-referential index
            - attributes are key values about the node (name)

            A graph described with indicies along does not require semantics. We can
            shove all model specific semantics into the attributes. Common attributes
            can be declared and made more canonical: name, op_type.

            [ { inputs:[], outputs:[], index: _idx_, attributes: {} } ]
        '''

        nodes = self.collect_all_nodes()
        name_to_idx = {}
        idx_counter = 0


        def get_idx(name):
            nonlocal idx_counter
            if name not in name_to_idx:
                name_to_idx[name] = idx_counter
                idx_counter += 1
            return name_to_idx[name]

        indexed_nodes = []
        for i, node in enumerate(nodes):
            indexed_nodes.append({
                'idx': i,
                'input': [get_idx(t) for t in node['input']],
                'output': [get_idx(t) for t in node['output']],
                'attrs': {
                    'op_type': node['op_type'],
                    'name': node['name'],
                }
            })

        idx_to_name = {v: k for k, v in name_to_idx.items()}
        return indexed_nodes, idx_to_name


    '''
    (Pdb) nodes = obj.collect_all_nodes()
    '''

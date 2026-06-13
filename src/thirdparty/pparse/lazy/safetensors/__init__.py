from __future__ import annotations

import logging
from typing import Any, Optional, Type

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.safetensors.state import (
    SafetensorsParsingLength,
    SafetensorsParsingTensorNode,
    SafetensorsParsingState,
)


def configure_pparser(**kwargs: Any) -> Type[pparse.Parser]:

    class Parser(pparse.Parser):


        @staticmethod
        def match_extension(fname: str) -> bool:
            if not fname:
                return False
            for ext in [".safetensors"]:
                if fname.endswith(ext):
                    return True
            return False


        @staticmethod
        def match_magic(cursor: pparse.Cursor) -> bool:
            # TODO: 8 bytes of offset til '}', then '{'.
            return False


        def make_root_node(
            self,
            parent: Optional[pparse.Node] = None,
            init_state: Type[SafetensorsParsingState] = SafetensorsParsingLength,
        ) -> pparse.Node:
            init_state = self._init_state_as_cls(init_state)

            # Current path of pending things.
            root = pparse.Node(self._source.open(), self, default_value={}, parent=parent)
            root.ctx()._next_state(init_state)
            return root


        def __init__(self, source: pparse.Extraction, id: str = "safetensors") -> None:
            super().__init__(source, id, SafetensorsParsingState)


        @staticmethod
        def from_fpath(fpath: str) -> pparse.Parser:
            data_source = pparse.FileData(path=fpath)
            data_range = pparse.Range(data_source.open(), data_source.length)
            extraction = pparse.BytesExtraction(name=fpath, reader=data_range)
            return Parser(extraction)


        def tensor_node_from(
            self, tensor_reader: pparse.Reader, node: pparse.Node, header_key: str, header_node: pparse.Node
        ) -> pparse.Node:

            # TODO: I don't like this.
            header_length = node.value['header_length']
            (start, end) = header_node._value['data_offsets']._value
            # Seek to the start offset of tensor data
            tensor_reader.seek(8 + header_length + start)
            # Create range from current position of tensor_reader
            tensor_range = pparse.Range(tensor_reader, end - start)
            # Create node with new range
            tensor_node = pparse.Node(tensor_range, node.ctx().parser(), parent=node)
            # Set the handling state.
            # tensor_node.ctx().header_key = header_key
            tensor_node.ctx()._next_state(SafetensorsParsingTensorNode)

            return tensor_node

        # def _scan_children(self):
        #     try:
        #         for extraction in self.source()._extractions:
        #             extraction.discover_parsers(Parser.PARSER_REGISTRY).scan_data()
        #     except pparse.EndOfDataException:
        #         log.debug("END OF DATA")
        #         pass
        #     except Exception as e:
        #         log.debug(e)
        #         import traceback

        #         traceback.print_exc()

        # def scan_data(self):
        #     # While not end of data, keep parsing via states.
        #     try:
        #         while True:
        #             self.current.ctx().state().parse_data(self, self.current.ctx())
        #     except pparse.EndOfNodeException as e:
        #         pass
        #     except pparse.EndOfDataException as e:
        #         pass
        #     except pparse.UnsupportedFormatException:
        #         raise

        #     # Scan all the extractions.
        #     self._scan_children()

        #     log.debug("DONE SCANNING CHILDREN")

        #     # TODO: Consider traversing all tensors in safetensors and creating
        #     # nodes that point to tensor data in the original Data

        #     return self

    return Parser

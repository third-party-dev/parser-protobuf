#!/usr/bin/env python3

from __future__ import annotations

import io
import logging
from typing import Any, Optional, Type

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.pickle.state import PickleParsingPickleStream, PickleParsingState
from thirdparty.pparse.lazy.pickle.node import Node

def configure_pparser(**kwargs: Any) -> Type[pparse.Parser]:

    class Parser(pparse.Parser):
        @staticmethod
        def match_extension(fname: str) -> bool:
            if not fname:
                return False
            # for ext in ['.onnx']:
            for ext in [".pkl"]:
                if fname.endswith(ext):
                    return True
            return False

        @staticmethod
        def match_magic(cursor: pparse.Cursor) -> bool:
            return False


        def make_root_node(self, parent: Optional[pparse.Node] = None, init_state: Type[PickleParsingState] = PickleParsingPickleStream) -> Node:
            init_state = self._init_state_as_cls(init_state)

            root = Node(self._source.open(), self, default_value=[], parent=parent)
            root.ctx()._next_state(init_state)
            return root


        def __init__(self, source: pparse.Extraction, id: str = "pkl") -> None:
            super().__init__(source, id, PickleParsingState)

        @staticmethod
        def from_reader(reader: pparse.Reader) -> pparse.Parser:
            extraction = pparse.BytesExtraction(name="data.zip", reader=reader.dup())
            return Parser(extraction)


        @staticmethod
        def from_bytesio(bytes_io: io.BytesIO) -> pparse.Parser:
            data_source = pparse.BytesIoData(bytes_io=bytes_io)
            data_range = pparse.Range(data_source.open(), data_source.length)
            extraction = pparse.BytesExtraction(name="data.pkl", reader=data_range)
            return Parser(extraction)


        def _end_container_node(self, node: pparse.Node) -> None:
            ctx = node.ctx()
            parent = ctx._parent
            if parent:
                log.debug(
                    f"end_container (off:{ctx.tell()}): Backtracking to parent {parent}."
                )

                # Set the end pointer to advance parent past field.
                ctx.mark_end(node)

                # In parent, fast forward past the bit we just parsed.
                parent.ctx().seek(ctx._end)

                # # Kill ctx (hopefully reclaiming memory).
                # node.clear_ctx()

                # # Set current node to parent.
                # self.current = parent

        def scan_data(self) -> pparse.Parser:
            # Do the opcodes first.
            try:
                while True:
                    # While not end of data, keep parsing via states.
                    self.current.ctx().state().parse_data(self, self.current.ctx())
            except pparse.EndOfNodeException:
                pass
            except pparse.EndOfDataException:
                pass
            except pparse.UnsupportedFormatException:
                raise

            # TODO: Do all the children.

            return self

    return Parser
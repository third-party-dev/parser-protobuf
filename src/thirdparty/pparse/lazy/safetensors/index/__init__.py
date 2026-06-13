from __future__ import annotations

import logging
from typing import Any, Optional, Type

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.safetensors.index.state import SafetensorsIndexParsingIndex, SafetensorsIndexParsingState


def configure_pparser(**kwargs: Any) -> Type[pparse.Parser]:

    class Parser(pparse.Parser):


        @staticmethod
        def match_extension(fname: str) -> bool:
            if not fname:
                return False
            for ext in [".json"]:
                if fname.endswith(ext):
                    return True
            return False


        @staticmethod
        def match_magic(cursor: pparse.Cursor) -> bool:
            return False


        def make_root_node(
            self,
            parent: Optional[pparse.Node] = None,
            init_state: Type[SafetensorsIndexParsingState] = SafetensorsIndexParsingIndex,
        ) -> pparse.Node:
            init_state = self._init_state_as_cls(init_state)

            root = pparse.Node(self._source.open(), self, default_value={}, parent=parent)
            root.ctx()._next_state(init_state)
            return root


        def __init__(self, source: pparse.Extraction, id: str = "safetensors_index") -> None:
            super().__init__(source, id, SafetensorsIndexParsingState)

    return Parser

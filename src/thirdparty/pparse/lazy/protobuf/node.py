#!/usr/bin/env python3

from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger(__name__)

# from thirdparty.pparse.lazy.protobuf import ProtobufParsingState, ProtobufParsingKey
import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lib import NodeContext as BaseNodeContext


class NodeContext(BaseNodeContext):
    def __init__(self, parent: Optional[pparse.Node], reader: pparse.Range, parser: pparse.Parser) -> None:
        if type(reader).__name__ != "Range":
            raise Exception("protobuf NodeContext reader must be a pparse.Range")
        super().__init__(parent, reader, parser)
        self._key: Any = None
        self._type_desc: Any = None

    def type_desc(self) -> Any:
        return self._type_desc

    def key(self) -> Any:
        return self._key

    def set_key(self, field: Any) -> None:
        self._key = field

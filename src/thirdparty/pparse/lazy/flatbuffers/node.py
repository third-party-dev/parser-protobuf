#!/usr/bin/env python3

from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
#from thirdparty.pparse.lib import NodeContext as BaseNodeContext


class NodeContext(pparse.NodeContext):
    def __init__(self, parent: Optional[pparse.Node], reader: pparse.Reader, parser: pparse.Parser) -> None:
        super().__init__(parent, reader, parser)

        self._type_desc: Any = None
        self._abs_off: Optional[int] = None

        self._fields_created: bool = False

    def type_desc(self) -> Any:
        return self._type_desc

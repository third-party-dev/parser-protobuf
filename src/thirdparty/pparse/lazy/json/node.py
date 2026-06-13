#!/usr/bin/env python3

from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse


class NodeContext(pparse.NodeContext):


    def __init__(self, node: Optional[pparse.Node], parent: pparse.Reader, reader: pparse.Parser) -> None:
        super().__init__(node, parent, reader)
        self._key_reg: Optional[str] = None
        self.json_top: bool = False


    def key(self) -> Optional[str]:
        return self._key_reg


    def set_key(self, v: Optional[str]) -> NodeContext:
        self._key_reg = v
        return self

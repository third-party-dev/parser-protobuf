from __future__ import annotations

import logging
from typing import Any, Optional, Type

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.om.state import OmParsingHeader, OmParsingState

'''
OM doesn't have a clear specification. What I'm comfortable building out:

States:
  - header     NodeMap
    - TBD: primary header
    - TBD: header extension
  - partition table    NodeArray
    - partition          NodeMap
      - model_def        NodeMap
        - model_def header   NodeMap
        - model_def protobuf
        - type, size, offset
        - raw_data

      - [other partitions]
        - type, size, offset
        - raw_data
'''

def configure_pparser(**kwargs: Any) -> Type[pparse.Parser]:

    class Parser(pparse.Parser):
        @staticmethod
        def match_extension(fname: str) -> bool:
            if not fname:
                return False
            for ext in [".om"]:
                if fname.endswith(ext):
                    return True
            return False

        @staticmethod
        def match_magic(cursor: pparse.Cursor) -> bool:
            return False

        def make_root_node(self, parent: Optional[pparse.Node] = None, init_state: Type[OmParsingState] = OmParsingHeader, ctx_args: dict[str, Any] = {}) -> pparse.Node:
            init_state = self._init_state_as_cls(init_state)

            root = pparse.Node(self._source.open(), self, parent=parent, ctx_class=pparse.NodeContext, ctx_args=ctx_args)
            root.ctx()._next_state(init_state)
            return root

        def __init__(self, source: pparse.Extraction, id: str = "om") -> None:
            super().__init__(source, id, OmParsingState)

        def new_map_node(self, node: pparse.Node) -> pparse.Node:
            return pparse.Node(node.ctx().reader(), self, parent=node, default_value={})

        def new_array_node(self, node: pparse.Node) -> pparse.Node:
            return pparse.Node(node.ctx().reader(), self, parent=node, default_value=[])

        # def _new_nodemap(self, parent, reader):
        #     return NodeMap(parent, reader)
        
        # def _new_nodearray(self, parent, reader):
        #     return NodeArray(parent, reader)

        # def _apply_value(self, ctx, field, value):
        #     if isinstance(self.current, NodeArray):
        #         log.debug(
        #             f"apply_value (off:{ctx.tell()}): Inside {self.current}. Append value."
        #         )
        #         self.current.value.append(value)
        #         return

        #     elif isinstance(self.current, NodeMap):
        #         # TODO: Is this a good place to determine if we Node-ify a value?

        #         log.debug(
        #             f"apply_value (off:{ctx.tell()}): Inside {self.current}. Set value to key {field.name}."
        #         )
        #         self.current.value[field] = value
        #         return

        #     log.debug(
        #         f"UNLIKELY!! apply_value (off:{ctx.tell()}): Create arr as top level object."
        #     )
        #     breakpoint()

        # def _start_map_node(self, ctx):
        #     parent = self.current
        #     # BUG: When we get a cursor, we're getting a duplicate of the cursor and its _current_ offset.
        #     # BUG: When we get a range, we're getting a duplicate of the range with the original offset?!
        #     newmap = NodeMap(parent, ctx.reader())
        #     newmap.ctx().skip(1)

        #     if ctx.key():
        #         log.debug(
        #             f"start_map (off:{ctx.tell()}): Found key, assuming in Map. Add new map to current map."
        #         )
        #         parent.value[ctx.key()] = newmap
        #         self.current = parent.value[ctx.key()]
        #         ctx.set_key(None)
        #     elif isinstance(self.current, NodeArray):
        #         log.debug(
        #             f"start_map (off:{ctx.tell()}): Inside Array. Append new map to current array."
        #         )
        #         self.current.value.append(newmap)
        #         self.current = newmap
        #     else:
        #         log.debug(f"start_map (off:{ctx.tell()}): Create map as top level object.")
        #         parent.value = newmap
        #         self.current = newmap

        # def _start_array_node(self, ctx):
        #     newarr = NodeArray(self.current, ctx.reader())
        #     newarr.ctx().skip(1)

        #     if ctx.key():
        #         log.debug(
        #             f"start_arr (off:{ctx.tell()}): Found key, assuming in Map. Add new arr to current map."
        #         )
        #         self.current.value[ctx.key()] = newarr
        #         self.current = self.current.value[ctx.key()]
        #         ctx.set_key(None)
        #     elif isinstance(self.current, NodeArray):
        #         log.debug(
        #             f"start_arr (off:{ctx.tell()}): Inside Array. Append new arr to current array."
        #         )
        #         self.current.value.append(newarr)
        #         self.current = newarr
        #     else:
        #         log.debug(f"start_arr (off:{ctx.tell()}): Create arr as top level object.")
        #         self.current = newarr

        # def _end_container_node(self, ctx):
        #     parent = ctx._parent
        #     if parent:
        #         log.debug(f"end_container (off:{ctx.tell()}): Backtracking to parent.")

        #         # Set the end pointer to advance parent past field.
        #         ctx.mark_end()

        #         # Fast forward past the bit we just parsed.
        #         parent.ctx().seek(ctx._end)

        #         # Kill ctx (hopefully reclaiming memory).
        #         ctx.node().clear_ctx()

        #         # Set current node to parent.
        #         self.current = parent
        #     # else:
        #     #     log.debug("end_container: Backtracking to initial node.")

        #     #     # Set the end pointer to advance parent past field.
        #     #     ctx.mark_end()

        #     #     # Kill ctx (hopefully reclaiming memory).
        #     #     ctx.node().clear_ctx()

        def scan_data(self) -> pparse.Parser:
            # While not end of data, keep parsing via states.
            try:
                while True:
                    #                                    (parser, ctx )
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
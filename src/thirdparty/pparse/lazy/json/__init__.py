from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.json.state import JsonParsingStart, JsonParsingState


'''
    self._extraction._parser['json']._root.load()

'''

"""
    Roles:
    - **Data** points to _data source_ (i.e. a shared file descriptor).
    - **Reader** is something that can tell, seek, skip, peek, read, and dup.
    - **Cursor** is an unbounded offset into a data source (isa Reader).
    - **Range** has start, cursor, and length of data source (isa Reader)
    - **Extraction** is _named_ range of data to link with Parsers.
    - **pparse** generates (initial) **Extraction** from **Data**
    - **pparse** discovers and assigns **Parsers** to **Extractions**
    - **Parser** parses data as node tree within parser associated Extraction.
    - Do we keep parser state when complete? (I think no.)
    - **Parsers** generate sub-Extractions from Extraction
    - Sub-**Extraction** stored in parent **Extraction**
    - Sub-**Extraction** may point to node (must be strong reference?).

    Nodes are dumb:
    - Each node has (at most) 4 references: start, length, meta, _data_.
    - Point to start and length of data (but **not** the data).
    - `meta` is None when parser is done with Node.
    - _data_ is node sub-type specific ({} for Map, [] for Array)
    - Depends on Parser for all processing. (i.e. its state for Parser)
    - State or Data Type of the Node is implicit in the Node subclass.

    Parsers and their Node trees are tightly coupled.
    The parser and node tree are linked by the Extraction object.

    Different Format Approaches To Consider:
    - JSON is not length delimited, therefore must be **depth-first**.
    - Protobuf is length delimited, can be breadth first.

    - Flexbuffers/Flatbuffers - oob tables, may require non-continugous ranges.
    - Flexbuffers - Length delimited, bottom up. (Leaves parsed first.)
    - Flatbuffers - Length delimited, top down. (Ancestors parsed first.)

"""


"""
    I feel like this code base is 33% there. I've now successfully broken up the
    main loop code from the actual node tree that does the parsing. The current
    issue is we don't have a way for the nodes to parse themselves in isolation
    from the rest of the tree.

    Ideally, the nodes will minimize the state that they keep about themselves:

    - Reader - Initially Cursor, Range when length known.
    - A Range gets us start, end, and length.
    - Keeping Range in temporary and only saving start and end saves a reference.
        The parser has the artifact and therefore the Data object we'd used to
        generate the Range.
    - State - TODO: State should be inferred by type.

    - Temporary meta for runtime parsing, should be reclaimed when done.
    - All temporary data could be kept in a Node.temp dictionary.
    - Parent - required for rewinding while parsing
        - Parent references can be used for ref counting, but no concern now.
    - Key-reg - Nodes only need key reg when building map entries
    - child - A weird one only used by root... need a new LazyJsonParserRootNode
    - value - Need a new LazyJsonParser{TYPE}Node

    Nodes have states: scanning -> shelf -> parsing -> loaded -> shelf -> ...
"""

# Consider:
# def make_json_parser():
#     class Parser(pparse.Parser):
#         ...
#     return Parser

def configure_pparser(**kwargs: Any) -> Type[pparse.Parser]:

    class Parser(pparse.Parser):
        # RULE: Parser knows extensions
        @staticmethod
        def match_extension(fname: str) -> bool:
            if not fname:
                return False
            for ext in [".json"]:
                if fname.endswith(ext):
                    return True
            return False

        # RULE: Parser knows magic
        @staticmethod
        def match_magic(cursor: pparse.Cursor) -> bool:
            return False


        def make_root_node(self, parent: Optional[pparse.Node] = None, init_state: Type[JsonParsingState] = JsonParsingStart, ctx_args: Dict[str, Any] = {}) -> pparse.Node:
            init_state = self._init_state_as_cls(init_state)

            from thirdparty.pparse.lazy.json.node import NodeContext
            root = pparse.Node(self._source.open(), self, parent=parent, ctx_class=NodeContext, ctx_args=ctx_args)
            root.ctx()._next_state(init_state)
            return root


        def __init__(self, source: pparse.Extraction, id: str = "json") -> None:
            super().__init__(source, id, JsonParsingState)

        @staticmethod
        def from_reader(reader: pparse.Reader) -> pparse.Parser:
            extraction = pparse.BytesExtraction(name="data.json", reader=reader.dup())
            return Parser(extraction)


        def apply_node_value(self, node: pparse.Node, value: Any) -> None:
            ctx = node.ctx()

            if ctx.key():
                log.debug(f"apply_val: Inside map, unset keyreg, set value ({value})")
                node._value[ctx.key()] = value
                ctx.set_key(None)

            elif callable(getattr(node._value, "append", None)):
                log.debug(f"apply_val: Inside arr, append value ({value})")
                node._value.append(value)

            elif isinstance(node._value, dict) and ctx.key() is None:
                log.debug(f"apply_val: Inside map, setting key reg ({value})")
                ctx.set_key(value)

            else:
                log.debug(f"apply_val: Top level or on-demand loading, set value ({value})")
                # breakpoint()
                # Note: This implicitly covers the root node case.
                node._value = value


        def new_array_node(self, parent: pparse.Node, ctx_args: Dict[str, Any] = {}) -> pparse.Node:
            # TODO: Consider alternative ctx()._state management? Currently set by State object.
            from thirdparty.pparse.lazy.json.node import NodeContext
            return pparse.Node(parent.ctx().reader(), self, default_value = [], parent = parent, ctx_class = NodeContext, ctx_args = ctx_args)


        def new_map_node(self, parent: pparse.Node, ctx_args: Dict[str, Any] = {}) -> pparse.Node:
            # TODO: Consider alternative ctx()._state management? Currently set by State object.
            from thirdparty.pparse.lazy.json.node import NodeContext
            return pparse.Node(parent.ctx().reader(), self, default_value = {}, parent = parent, ctx_class = NodeContext, ctx_args = ctx_args)


        def new_root_node(self, node: pparse.Node, ctx_args: Dict[str, Any] = {}) -> pparse.Node:
            from thirdparty.pparse.lazy.json.node import NodeContext
            return pparse.Node(node.ctx().reader(), self, default_value = {}, parent = node.ctx().parent(), ctx_class = NodeContext, ctx_args = ctx_args)


        def _end_container_node(self, node: pparse.Node) -> None:
            ctx = node.ctx()
            parent = ctx._parent
            if parent:
                log.debug(f"end_container (off:{ctx.tell()}): Backtracking to parent.")

                # Set the end pointer to advance parent past field.
                ctx.mark_end(node)

                # Fast forward past the bit we just parsed.
                parent.ctx().seek(ctx._end)

                # # Kill ctx (hopefully reclaiming memory).
                # node.clear_ctx()

                # Set current node to parent.
                #self.current = parent
            # else:
            #     log.debug("end_container: Backtracking to initial node.")

            #     # Set the end pointer to advance parent past field.
            #     ctx.mark_end()

            #     # Kill ctx (hopefully reclaiming memory).
            #     ctx.node().clear_ctx()

        # def scan_data(self):
        #     # While not end of data, keep parsing via states.
        #     try:
        #         while True:
        #             #                                    (parser, ctx )
        #             self.current.ctx().state().parse_data(self, self.current.ctx())
        #     except pparse.EndOfNodeException as e:
        #         pass
        #     except pparse.EndOfDataException as e:
        #         pass
        #     except pparse.UnsupportedFormatException:
        #         raise

        #     # TODO: Do all the children.

        #     return self

    return Parser
"""Node — the core data unit of the pparse parse-tree."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Type
from .reader import Reader, Range
from .constants import AGAIN, NEXT
from .exceptions import (
    EndOfNodeException,
    EndOfDataException,
    UnsupportedFormatException,
)
from .node_context import NodeContext

# TODO: Dumper should not be using thirdparty.pparse.lib if called here.
from thirdparty.pparse.dump import Dumper

if TYPE_CHECKING:
    from .parser import Parser


class UnloadedValue:
    """Sentinel object used as the default value of a ``Node`` before it is parsed.

    A single module-level instance ``UNLOADED_VALUE`` is used everywhere.
    """


    def __repr__(self) -> str:
        return "<UNLOADED_VALUE />"


UNLOADED_VALUE = UnloadedValue()


class RecursionControl:
    """Configurable guard that limits how deeply ``Node.load`` recurses.

    ``RecursionControl`` is passed to ``Node.load`` to give callers
    fine-grained control over which parts of the parse tree are eagerly
    expanded.  At each node, ``stopped`` is called to decide whether
    recursion should halt.

    Args:
        min_depth: Nodes at depths below this value are always loaded,
            ignoring ``max_depth`` and the callback.
        max_depth: Nodes at depths above this value are never loaded.
        callback: An optional callable that receives a ``Node`` and returns
            ``True`` to stop recursion at that node.  Only called when
            ``min_depth <= cur_depth <= max_depth``.
    """

    MAX_DEPTH = 9223372036854775807


    def __init__(
        self, min_depth: int = 0, max_depth: int = MAX_DEPTH, callback: Optional[Callable[[Node], bool]] = None
    ) -> None:
        self.cur_depth = 0

        self.max_seen_depth = 0

        self.min_depth = min_depth
        self.max_depth = max_depth
        self.cb = callback


    def stopped(self, node: Node) -> bool:
        """Return whether recursion should halt at ``node``.

        Args:
            node: The ``Node`` that is about to be loaded.

        Returns:
            ``True`` if loading ``node`` should be skipped, ``False`` if it
            should proceed.  Returns ``None`` (falsy) when depth is within
            the min/max window and no callback is configured.
        """
        if self.cur_depth < self.min_depth:
            return False
        if self.cur_depth > self.max_depth:
            return True

        if self.cb is not None:
            return self.cb(node)


    def increase_depth(self, amount: int = 1) -> None:
        """Increment the current recursion depth and update the high-water mark.

        Args:
            amount: Number of levels to increase by.
        """
        self.cur_depth += amount
        if self.cur_depth > self.max_seen_depth:
            self.max_seen_depth = self.cur_depth


    def decrease_depth(self, amount: int = 1) -> None:
        """Decrement the current recursion depth.

        Args:
            amount: Number of levels to decrease by.
        """
        self.cur_depth -= amount


    def current_depth(self) -> int:
        """Return the current recursion depth.

        Returns:
            The number of ``load`` calls currently on the call stack.
        """
        return self.cur_depth


    def deepest_depth(self) -> int:
        """Return the maximum recursion depth seen since this instance was created.

        Returns:
            The high-water mark for recursion depth.
        """
        return self.max_seen_depth


'''
    NEW PLAN:
    - phase 1: ctx is always loaded and node always UNLOADED until parent says otherwise
    - phase 2: ctx can be archived and unloaded (optionally cleared archive)
               root node always has ctx
    - phase 3: ability to replay from root to re-acquire ctx

    Things To Work Out:
    - we can prefer to not parse until referenced by using .value, but if we want to 
      intentionally pre-parse everything, we need a load(recursive=True) or something.
    - with new plan, we should have generic node for 99% of cases. NodeContext is the parser
      specific class going forward. (maybe a generic self._attrs:dict required at node level)
'''


class Node:
    """A single node in the pparse parse-tree.

    A ``Node`` represents a region of binary data that a ``Parser`` knows about
    and _possibly_ how to interpret.  Its ``_value`` starts as ``UNLOADED_VALUE`` and is
    populated lazily on first access via the ``value`` property, which
    triggers ``load()``.

    Each node owns a ``NodeContext`` that carries the parser's state machine (for the Node)
    and a ``Reader`` positioned at the start of the node's data offset.

    Args:
        reader: A ``Reader`` positioned at the start of this node's data.
        parser: The ``Parser`` responsible for interpreting this node.
        default_value: Initial value; defaults to ``UNLOADED_VALUE`` so that
            the node is parsed lazily on first access.
        parent: The parent ``Node``, or ``None`` for the root.
        ctx_class: An optional ``NodeContext`` subclass to instantiate instead
            of the default ``NodeContext``.
        ctx_args: Extra keyword arguments forwarded to ``ctx_class``.
    """


    def __init__(
        self,
        reader: Reader,
        parser: Parser,
        default_value: Any = UNLOADED_VALUE,
        parent: Optional[Node] = None,
        ctx_class: Optional[Type[NodeContext]] = None,
        ctx_args: Dict[str, Any] = {},
    ) -> None:

        # Reference to the start of data for parsing node.
        self._reader = reader.dup()

        '''
            weird situation here where I don't want to double bind Node and 
            NodeContext, but they are indirectly double bound by NodeContext
            knowing parent of node. This is intentional so that we can throw
            away unnecessary references to parents later.
        '''

        # Reference to the parser in context of node.
        if not ctx_class:
            self._ctx = NodeContext(parent, reader.dup(), parser)
        else:
            self._ctx = ctx_class(parent, reader.dup(), parser, **ctx_args)

        # Reference to the value(s) of node (e.g. dict, list, scalars, or Node)
        self._value = default_value


    @property
    def value(self) -> Any:
        """Return the parsed value, triggering ``load()`` if not yet parsed.

        Returns:
            The node's parsed value (dict, list, scalar, or nested ``Node``).
        """
        if self._value == UNLOADED_VALUE:
            # breakpoint()
            self.load()
        return self._value


    def ctx(self) -> NodeContext:
        """Return the ``NodeContext`` for this node.

        Returns:
            The ``NodeContext`` holding the parser state for this node.
        """
        return self._ctx


    def clear_ctx(self) -> Node:
        """Release the ``NodeContext`` to free memory.

        Should only be called once the node's value is fully loaded and
        re-parsing is no longer needed or acceptably thrown away for restoration
        of memory.

        Returns:
            ``self``, to allow chaining.
        """
        # TODO: Archive context here. Archive in parser?
        self._ctx = None
        return self


    def tell(self) -> int:
        """Return the absolute byte offset of the start of this node's data.

        Returns:
            The node's start position within the data source.
        """
        return self._reader.tell()


    def set_length(self, length: int) -> Node:
        """Replace the internal reader with a ``Range`` of ``length`` bytes.

        Args:
            length: Number of bytes in this node's data region.

        Returns:
            ``self``, to allow chaining.
        """
        self._reader = Range(self._reader.dup(), length)
        return self


    def length(self) -> int:
        """Return the byte length of this node's data region.

        Returns:
            The number of bytes in the node's ``Range``.
        """
        # TODO: Check for range?
        return self._reader.length()


    def load(self, recursion: Optional[RecursionControl] = None) -> Optional[Node]:
        """Parse this node's data region and populate ``_value``.

        Drives the parser state machine until ``EndOfNodeException`` (success),
        ``EndOfDataException`` (propagated), or ``UnsupportedFormatException``
        (propagated) is raised.  Whenever the state machine registers
        descendant nodes they are immediately loaded in depth-first order,
        subject to ``recursion`` constraints.

        ``load()`` manages ``RecursionControl`` lifetime, enabling different
        behaviors per call and managing recursion depth relative to the
        current node.

        CAUTION: Recursion control is a mechanism that allows parsers to delegate recursion
        decisions to the caller or user of the API. It does not enforce or provide
        tight controls over the parts of the Node tree that get processed.

        RULE: load() should handle the recursive behavior, not the parser state.

        RULE: Leaky abstraction when recursion policy stored in Node or NodeContext!

        NOTE: json parsing is weird because you have to recurse every time. Since I
        implemented JSON first, I believe its driving some of the anti-patterns in pparse.
        If we want to save on memory for JSON, we could theoretically parse and allocate
        nodes and as we complete branches of a depth first parse we deallocated.
        I naturally want to do this for recursive=False, but since recursive=False
        is default, it makes it feel like unnecessary thrashing of the CPU.

        Args:
            recursion: An optional ``RecursionControl`` that limits how deeply
                the parse tree is expanded.  When ``None`` all reachable
                descendants are loaded eagerly.

        Returns:
            ``self`` if loading completed, ``None`` if ``recursion`` halted
            loading before any state was run.

        Raises:
            EndOfDataException: If the data source is exhausted unexpectedly.
            UnsupportedFormatException: If the data does not match the expected
                format.
        """

        # Increment the depth on entrance to load().
        # NOTE: Checking for recursion here because we don't want to mess with reentrant
        #       states and we don't want to wipe or confuse _descendants todo lists.
        # CAUTION:
        # - states can add multiple branches at once.
        # - states can iterate multiple times in a single "depth level"
        if recursion is not None:
            if recursion.stopped(self):
                return
            recursion.increase_depth()
            # print(f"INCREASE {recursion.cur_depth}")

        # Maybe a naughty pattern, but for now we retry until
        # Retry until state returns UnsupportedFormatException or EndOfNodeException
        # ! When EndOfDataException raised, we need a way to retry. For now, fail.
        try:
            # RULE: AGAIN is a Parser return. Not a Node is complete status!
            res = AGAIN
            while res in (AGAIN, NEXT):
                if res == NEXT and len(self.ctx()._state_stack) > 1:
                    # Throw it away.
                    self.ctx()._pop_state()

                res = self.ctx().state().parse_data(self)

                '''
                    - The parser is responsible for populating _decendents.
                    - Whenever Node.load() sees elements in _decendents, it immediately
                    calls the load() method on those elements.
                '''
                while self.ctx()._descendants:
                    # ! Here, we're making Node responsible for _descendants cleanup.
                    child = self.ctx()._descendants.pop(0)

                    # TODO: use try/except to push forward, even on failure.
                    # TODO: we should be able to track failures for retry later.
                    child.load(recursion=recursion)

        except EndOfNodeException:
            pass
        except EndOfDataException:
            raise
        except UnsupportedFormatException:
            raise

        finally:
            # Decrement the depth on exit from load() (exceptions included).
            if recursion is not None:
                recursion.decrease_depth()
                # print(f"DECREASE {recursion.cur_depth}")

        return self


    def unload(self) -> None:
        global UNLOADED_VALUE
        """Reset this node's value to ``UNLOADED_VALUE`` so it can be re-parsed when needed."""
        # TODO: Do we have context?
        self.value = UNLOADED_VALUE


    def dump(self, depth: int = 0, step: int = 2, dumper: Any = None) -> None:
        """Render this node to the given dumper for debugging or serialization.

        Args:
            depth: Current indentation depth passed to the dumper.
            step: Number of spaces per indentation level.
            dumper: A ``Dumper`` instance; ``Dumper.default()`` is used when
                this is ``None``.
        """
        node_attrs = [f'off="{self.tell()}"']

        if not dumper:
            dumper = Dumper.default()
        dumper.dump("Node", self._value, ' '.join(node_attrs), depth=depth, step=step)


    @classmethod
    def from_xml(cls, src_xml: Any, ctx_ref: Any) -> Optional[Node]:
        """Reconstruct a ``Node`` from a ``<node />`` XML element.

        Reads parser, context, and value information from the XML, resolves
        the appropriate parser via a built-in registry, and recursively
        deserializes any nested ``<node />`` values.

        Args:
            src_xml: A ``<node />`` XML element or string.
            ctx_ref: A ``ContextRef`` carrying the parent result reference,
                optional context XML, and resolved parser.

        Returns:
            The reconstructed ``Node``, or ``None`` if the node has no
            ``<value />`` element (i.e. is left in the unloaded state).

        Raises:
            Exception: If the element is not a ``<node />`` or required
                attributes are missing.
        """
        from thirdparty.pparse._xml import XmlNode, XmlEntry

        node_xml = XmlNode.as_node(src_xml)

        if not node_xml.has_tag('node'):
            raise Exception(f"Expected <node />, got: {node_xml}")

        # reader = ctx_ref.result_ref.extraction._reader.dup()

        # offset = None
        # length = None
        # # TODO: Get reference to extraction datasource.
        # if xml.has_attr("offset") and xml.has_attr("length"):
        #     # use range
        #     offset = int(xml['offset'])
        #     length = int(xml['length'])

        #     cursor = Cursor(data, offset)
        #     reader = Range(cursor, length)
        # elif xml.has_attr("offset"):
        #     # use cursor
        #     offset = int(xml['offset'])
        #     reader = Cursor(data, offset)
        # else:
        #     raise Exception("Expected offset in <node />")

        # Get context data here because we init context with Node constructor.
        # ctx_class = NodeContext
        # ctx_args = {}
        # parser_name = None
        # state_name = None

        # ! -----------------------------------------------------------------------------------------------------------
        # ! Ok for development, but this needs to be done at runtime with a user provided allow list.
        from thirdparty.pparse.lazy.flatbuffers import configure_pparser as configure_flatbuffers_pparser
        from thirdparty.pparse.lazy.json import configure_pparser as configure_json_pparser
        from thirdparty.pparse.lazy.om import configure_pparser as configure_om_pparser

        # from thirdparty.pparse.lazy.onnx import configure_pparser as configure_onnx_pparser
        from thirdparty.pparse.lazy.pickle import configure_pparser as configure_pickle_pparser
        from thirdparty.pparse.lazy.protobuf import configure_pparser as configure_protobuf_pparser
        from thirdparty.pparse.lazy.pytorch import configure_pparser as configure_pytorch_pparser
        from thirdparty.pparse.lazy.safetensors import configure_pparser as configure_safetensors_pparser
        from thirdparty.pparse.lazy.safetensors.index import configure_pparser as configure_safetensors_index_pparser
        from thirdparty.pparse.lazy.zip import configure_pparser as configure_zip_pparser

        parser_registry = {
            'thirdparty.pparse.lazy.flatbuffers': configure_flatbuffers_pparser,
            'thirdparty.pparse.lazy.json': configure_json_pparser,
            'thirdparty.pparse.lazy.om': configure_om_pparser,
            #'thirdparty.pparse.lazy.onnx': configure_onnx_pparser,
            'thirdparty.pparse.lazy.pickle': configure_pickle_pparser,
            'thirdparty.pparse.lazy.protobuf': configure_protobuf_pparser,
            'thirdparty.pparse.lazy.pytorch': configure_pytorch_pparser,
            'thirdparty.pparse.lazy.safetensors': configure_safetensors_pparser,
            'thirdparty.pparse.lazy.safetensors.index': configure_safetensors_index_pparser,
            'thirdparty.pparse.lazy.zip': configure_zip_pparser,
        }
        # ! -----------------------------------------------------------------------------------------------------------

        # If we were provided a parser reference, use it.
        parser_ref = ctx_ref.parser
        # context_state = None

        context_xml = node_xml.get("context")
        if context_xml is not None:
            if context_xml.has_attr('type'):
                raise Exception("custom context types not implemented for import yet")
                # TODO: Get the actual cls? throw if not in scope?
                # ctx_class = context_xml['type']

            if context_xml.get("extra"):
                # extra_xml = context_xml.extra
                # ctx_args = XmlEntry.as_map(extra_xml)
                pass

            parser_xml = context_xml.get('parser')
            # If we were given a parser descriptor in XML, use it instead.
            if parser_xml is not None:
                if not parser_xml.has_attr('type'):
                    raise Exception(f"<parser /> must have a type: {parser_xml}")
                if parser_xml['type'] not in parser_registry:
                    raise Exception(f"<parser /> type not in parser registry: {parser_xml}")

                if not parser_xml.has_attr('name'):
                    raise Exception(f"<parser /> must have a name: {parser_xml}")

                parser_args = {}
                if len(parser_xml) >= 1:
                    parser_args = XmlEntry.as_map(parser_xml)

                # Create a new parser.
                parser_factory = parser_registry[parser_xml['type']]
                parser_cls = parser_factory(**parser_args)
                parser_ref = parser_cls(ctx_ref.result_ref.extraction, parser_xml['name'])

            if context_xml.has_attr('state'):
                # TODO: Validate state against parser (which would should now have.)
                # context_state = context_xml['state']
                pass

        # Using make_root_node() to create the node, ignorant of parent, state, or context type.
        # TODO: Ensure all parsers support ctx_class and ctx_args if we want to create node with them.
        node = parser_ref.make_root_node()
        node_xml.set_obj_inst(node)

        # TODO: At this point we can opt to change the node's context state or other options.

        # Update context offsets based on Node offset.
        if node_xml.has_attr('offset'):
            node.ctx().skip(int(node_xml['offset']))
        # TODO: Consider changing reader from cursor to range?

        # Create a new ContextRef to push forward.
        # Update ctx_ref for value processing.
        # TODO: Consider performing this after parser_ref update (might save memory?)
        from thirdparty.pparse.lib.pparsexml import ContextRef

        ctx_ref = ContextRef(ctx_ref.result_ref, ctx_ref.context_xml, parser_ref)

        # TODO: Process the node's value from XML here. (Recursive.)
        value_xml = node_xml.get("value")
        if not value_xml:
            node._value = UNLOADED_VALUE
            return


        # Note: We pass a node_cb so that _xml.py doesn't get caught up in import races.
        def process_node_entry(ctx):


            def _process_node_entry(entry):
                if len(entry) != 1 or not entry.get("node"):
                    raise Exception("Expecting only <node /> in <entry type=\"node\" />.")

                node_xml = entry.node

                # TODO: Do better.
                node_cls = Node
                if node_xml.has_attr("type"):
                    node_cls = globals()[node_xml['type']]

                return node_cls.from_xml(node_xml, ctx)

            return _process_node_entry

        node_cb = process_node_entry(ctx_ref)
        # breakpoint()
        node._value = XmlEntry.using(value_xml, node_cb)

        return node
        '''
        <node offset="0" length="164892">
            <!-- (optional) for context parse replay (i.e. context initialization) -->
            <!-- when we don't know how to replay parsing, we go further up the tree until we do. -->
            <!-- if we reach root without seeing context init args, we let the parser decide. -->
            <!-- TODO: determine what this looks like in python -->
            <context parser="zip" state="complete" />
            <!-- every node has a value or `<unloaded_value />` -->
            <value type="node">
                <node offset="10" length="164882">
                    <value type="map">
                        <entry type="int" name="int_key">42</entry>
                        <entry type="float" name="float_key">3.14</entry>
                        <entry type="str" name="str_key">dance</entry>
                        <!-- entry is inherently json friendly, therefore type="json" -->
                        <!--   assumes the return should use json.loads -->
                        <entry type="json" name="json_key">
                            [1, 8, 16, 16]
                        </entry>
                        <!-- "normal" entry of type="list" has more entries -->
                        <entry type="list" name="list_key">
                            <entry type="int">1</entry>
                            <entry type="int">8</entry>
                            <entry type="int">16</entry>
                            <entry type="int">16</entry>
                        </entry>
                    </value>
                    <value type="node|map|list|str|int|float">value_here</value>
                </node>
            </value>
        </node>
        '''

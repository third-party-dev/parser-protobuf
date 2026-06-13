"""Extraction classes that couple a data source to one or more parsers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from .reader import (
    Reader,
)

if TYPE_CHECKING:
    from .node import Node
    from .parser import Parser

# Generic artifact that ties parsers to cursor-ed data.
class Extraction:
    """Abstract representation of a named data source with zero or more attached parsers.

    An ``Extraction`` couples a raw data source (file, URL, in-memory buffer) 
    with the parsers that know how to interpret it.  Subclasses implement
    ``open()`` to return a ``Reader`` positioned at the start of the data.

    Args:
        name: A human-readable name for this extraction (e.g. a filename).
        source: The parent this ``Extraction`` was derived from, if any.
    """


    def __init__(self, name: Optional[str] = None, source: Optional[Extraction] = None) -> None:
        # The extraction we came from. Detect parser via source.
        self._source: Optional[Extraction] = source
        self._name: Optional[str] = name  # name of extraction
        self._parser: Dict[str, Any] = {}  # parsers by id
        self._result: Dict[Any, Optional[Node]] = {}  # results by parser id
        self._extractions: list = []   # child extractions


    def name(self) -> Optional[str]:
        """Return the name of this extraction.

        Returns:
            The extraction name, or ``None`` if not set.
        """
        return self._name


    def set_name(self, name: str) -> Extraction:
        """Set the name of this extraction.

        Args:
            name: The new name.

        Returns:
            ``self``, to allow chaining.
        """
        self._name = name
        return self


    # ! adding parser to an extraction is the old way of thinking. Now, we want to add a new
    # ! potential result tree.
    # At this point, caller has identified a parser for the extraction. The system now
    # needs to create a result slot that will contain the root node of the result and
    # the root node will hold the initial parser instance (which gets copied to all
    # relevant children).
    def add_result(self, id: Any, root_node: Optional[Node]) -> None:
        """Register a root node against a result slot.

        Args:
            id: The result identifier (typically a string key).
            root_node: The root ``Node`` of the parse result, or ``None`` if
                the result has not been populated yet.
        """
        self._result[id] = root_node


    # TODO: Create passthrough load() for result or results
    def add_parser(self, id: str, parser: Optional[Parser]) -> None:
        """Register a parser under a string identifier.

        Args:
            id: A unique string key for this parser.
            parser: The ``Parser`` instance to register.
        """
        self._parser[id] = parser


    def has_parser(self, parser_id: str) -> bool:
        """Return whether a parser with the given ID has been registered.

        Args:
            parser_id: The parser identifier to check.

        Returns:
            ``True`` if a parser with that ID exists, ``False`` otherwise.
        """
        return parser_id in self._parser


    def discover_parsers(self, parser_registry: Dict[str, Any]) -> Extraction:
        """Auto-detect applicable parsers from a registry and register them.

        For each parser in ``parser_registry`` that has not already been
        registered, the method tries ``match_extension`` on the extraction
        name and then ``match_magic`` on the data bytes.  The first matching
        parser is instantiated and registered.

        Args:
            parser_registry: A mapping of parser ID strings to parser classes.

        Returns:
            ``self``, to allow chaining.
        """
        for pname, parser in parser_registry.items():
            if not self.has_parser(pname):
                if parser.match_extension(self.name()):
                    self.add_parser(pname, parser(self, pname))
                    continue
                if parser.match_magic(self.open()):
                    self.add_parser(pname, parser(self, pname))
                    continue

        return self


    def open(self) -> Reader:
        """Return a fresh ``Reader`` positioned at the start of the ``Extraction``'s data.

        Returns:
            A ``Reader`` ready for use at offset 0.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError()


    # Process all data at once.
    # TODO: Parse data lazily.
    # TODO: What is the interface that only parses what we need to?
    def scan_data(self) -> Extraction:
        """Trigger all registered parsers to scan the full data source.

        Note: Legacy/Unused

        Returns:
            ``self``, to allow chaining.
        """
        for parser in self._parser.values():
            parser.scan_data()
        return self


    # extraction = Extraction.from_xml("<job />")
    @classmethod
    def from_xml(cls, xml_src: Any, xml_root: Any) -> Extraction:
        """Load and resume ``Extraction`` from state in XML.

        Args:
            xml_src: An XML element or string describing the extraction.
            xml_root: The root XML context used to resolve references.

        Returns:
            A populated ``Extraction`` instance.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError("from_xml not implemented")


    # extraction.to_xml() -> "<job />"
    def to_xml(self) -> str:
        """Stop and save the current state of ``Extraction`` to XML.

        Returns:
            An XML string representation of this extraction.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError("to_xml not implemented")


# Generic artifact that ties parsers to cursor-ed data.
class BytesExtraction(Extraction):
    """An ``Extraction`` backed by an existing ``Reader`` (bytes already in hand).

    Used when the raw data is accessible via a ``Reader`` — for example, a
    ``Range`` wrapping a memory-mapped file or a ``BytesIoData`` cursor.
    Exactly one of ``source`` or ``reader`` must be provided.

    Args:
        name: A human-readable name for this extraction (e.g. relative filename).
        source: Parent ``Extraction`` to ``open`` a ``Reader``.
        reader: An existing ``Reader`` to use directly.

    Note: Use only source xor reader, not both (i.e. one and only one must be set).

    Raises:
        ValueError: If both or neither of ``source`` and ``reader`` are provided.
    """


    def __init__(
        self,
        name: Optional[str] = None,
        source: Optional[Extraction] = None,
        reader: Optional[Reader] = None,
    ) -> None:
        super().__init__(name, source)

        if (source is None and reader is None) or (source and reader):
            raise ValueError("Only one of source or data reader can be non-None.")
        if not source:
            # 'self' is the root Extraction.
            self._reader = reader.dup()
        if not reader:
            self._reader = source.open()

        # self._reader cursor is only used for dup() and tell()
        self._reader = reader


    def open(self) -> Reader:
        """Return ``Reader`` positioned at the start of the data.

        Returns:
            A duplicated ``Reader`` at offset 0.
        """
        return self._reader.dup()


    def tell(self) -> int:
        """Return the current byte offset of the internal reader.

        Returns:
            The current read position.
        """
        return self._reader.tell()


    # extraction = Extraction.from_xml("<job />")
    @classmethod
    def from_xml(cls, xml_src: Any, pparse_xml: Optional[Any] = None) -> BytesExtraction:
        """Load and resume a ``BytesExtraction`` from an XML element.

        Reads the ``<datasource />`` child element to create the underlying
        data object, wraps it in a ``Range``, and recursively processes any
        child extractions and result references.

        Args:
            xml_src: An XML element or string describing the extraction.
            pparse_xml: The parent ``PparseXml`` resolver, required when
                result references (``<result />``) are present.

        Returns:
            A populated ``BytesExtraction`` with its reader set up.

        Raises:
            Exception: If required attributes or elements are missing, or if
                result references are present but no resolver is provided.
        """

        from thirdparty.pparse._xml import XmlNode
        xml = XmlNode.as_node(xml_src)

        if not xml.has_attr("name"):
            raise Exception("extraction must have a name")
        name = xml['name']

        # XmlNode stores instances for parent<->child relationships.
        if not xml.get_parent().has_tag('child_extractions'):
            parent = None
        else:
            print("IMPLEMENT PARENT")
            breakpoint()
            # Assuming this gets us to source
            parent = xml.get_parent().get_parent()

        # ** Assuming extraction has datasource and datasource has type attribute.
        if xml.datasource['type'] not in locals():
            raise Exception(f"<datasource /> type {xml.datasource['type']} not in scope.")
        # ! -- Determine a "preferred" way to manage imports. (Ideally an allow list and dynamic.) --
        data_source = locals()[xml.datasource['type']].from_xml(xml.datasource)

        from thirdparty.pparse.lib import Range

        # TODO: Assuming Range for now.
        reader = Range(data_source.open(), data_source.length)

        # Likely: `extraction = BytesExtraction(name=name, source=source, reader=reader)`
        extraction = cls(name=name, source=parent, reader=reader)
        xml.set_obj_inst(extraction)

        if len(xml.results) and pparse_xml is None:
            raise Exception("Result references found, but missing reference resolver.")

        #extraction.result_refs = []
        for result_ref in xml.results:
            if not result_ref.has_attr('id'):
                raise Exception("All result references must have id attribute.")
            pparse_xml.add_result_ref(int(result_ref['id']), extraction)

        # Recurse into child extractions
        for child_extraction in xml.child_extractions:
            if not child_extraction.has_attr("type"):
                raise Exception("extraction must have a type attribute.")
            if child_extraction['type'] not in globals():
                raise Exception(f"child extraction type not in scope {child_extraction}")
            extraction_cls = globals()[child_extraction['type']]
            # ! Error, xml_root not defined.
            breakpoint()
            #child_extraction.set_obj_inst(extraction_cls.from_xml(child_extraction, xml_root))

        return extraction


    # extraction.to_xml() -> "<job />"
    def to_xml(self) -> str:
        raise NotImplementedError("to_xml not implemented")


# class FolderExtraction(Extraction):
#     def __init__(self, name: str = None, source: Optional['Extraction'] = None, path=None):

#         super().__init__(name, source)

#         if (source is None and reader is None) or (source and reader):
#             raise ValueError("Only one of source or data reader can be non-None.")
#         if not source:
#             # 'self' is the root Extraction.
#             self._reader = reader.dup()
#         if not reader:
#             self._reader = source.open()

#         # self._reader cursor is only used for dup() and tell()
#         self._reader = reader
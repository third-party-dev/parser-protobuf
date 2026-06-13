"""XML-driven import/export helpers that bridge pparse's object model and XML."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from thirdparty.pparse.lib import BytesExtraction

if TYPE_CHECKING:
    from thirdparty.pparse.lib.parser import Parser


# Job's only purpose is to facilitate kick off of XML import.
class PparseXml:
    """Coordinator for XML-driven import of a pparse parse session.

    ``PparseXml`` is instantiated once per ``<pparse />`` XML document.  It
    maintains a mapping from numeric result IDs to the ``BytesExtraction``
    objects that own those results, acting as a cross-reference resolver
    during the recursive import of ``<node />`` elements.

    Args:
        xml: The root XML node (or string) representing the ``<pparse />``
            document being imported.
    """


    def __init__(self, xml: Any) -> None:
        self.xml = xml

        # Table for reference matching
        self._result_ref_to_extraction: Dict[int, BytesExtraction] = {}


    def add_result_ref(self, result_ref_id: int, extraction: BytesExtraction) -> None:
        """Register map between result ID and ``Extraction``.

        Args:
            result_ref_id: The integer ``id`` attribute from a ``<result />``
                XML element.
            extraction: The ``BytesExtraction`` that owns the result.
        """
        self._result_ref_to_extraction[result_ref_id] = extraction


    def has_extraction(self, result_ref_id: int) -> bool:
        """Return whether a result ID has a registered extraction.

        Args:
            result_ref_id: The result ID to look up.

        Returns:
            ``True`` if the ID is registered, ``False`` otherwise.
        """
        return result_ref_id in self._result_ref_to_extraction


    def get_extraction(self, result_ref_id: int) -> BytesExtraction:
        """Return the extraction registered for a result ID.

        Args:
            result_ref_id: The result ID to look up.

        Returns:
            The ``BytesExtraction`` associated with ``result_ref_id``.
        """
        return self._result_ref_to_extraction[result_ref_id]


    # pparse xmls use pparse as the root element, but it is wrong to assume <pparse />
    # is the root of the xml we're working with. Instead, we assume its the top of the
    # scope pparse is able to process and reason about.
    @classmethod
    def from_xml(cls, xml_src: Any) -> PparseXml:
        """Load and resume from a ``<pparse />`` XML document into a live object graph.

        Recursively imports the root extraction, all result references, and
        all ``<node />`` elements, restoring the parser and context state for
        each node.

        Args:
            xml_src: A string, file path, or XmlNode representing the
                ``<pparse />`` document root.

        Returns:
            A fully populated ``PparseXml`` instance with all extraction and
            node references resolved.

        Raises:
            ValueError: If the root element is not ``<pparse />``.
            Exception: If required attributes or elements are missing.
        """

        # TODO: Consider xmlnode.py, xmlentry.py, and shoving this class in _xml.py.
        from thirdparty.pparse._xml import XmlNode

        # Ensure our parameters is an XmlNode
        xml = XmlNode.as_node(xml_src)

        # Store an instance of this class with our XmlNode.
        pparse_xml = xml.set_obj_inst(PparseXml(xml))

        if not xml.has_tag('pparse'):
            raise ValueError("root node is not <pparse /> in PparseXml class.")

        # TODO: Verify with schema.
        # TODO: Verify parsers.

        # Kick off parsing by instantiating the root extraction.
        if not xml.extraction.has_attr('type'):
            raise Exception("Extraction must have a type.")
        if xml.extraction['type'] not in globals():
            raise Exception(f"Extraction type {xml.extraction['type']} not in scope.")
        extraction_cls = globals()[xml.extraction['type']]
        xml.extraction.set_obj_inst(extraction_cls.from_xml(xml.extraction, pparse_xml))

        # Parse the results
        for result_xml in xml.results:
            # <result> should only ever have a single <node>
            # Note: <result> exists as a generic referable container for extractions.
            if len(result_xml) <= 0:
                continue
            if len(result_xml) > 1:
                # TODO: Should all results always contain a single node?
                raise Exception(f"more than 1 element found in result: {result_xml}")

            if not result_xml.has_attr('id'):
                raise Exception(f"All results must have id attribute: {result_xml}")
            result_ref = ResultRef(pparse_xml, result_xml)

            node_xml = result_xml.get('node')
            if node_xml is None:
                raise Exception(f"Non <node /> found in <result />: {result_xml}")

            from thirdparty.pparse.lib import Node

            # node type defaults to (pparse) Node
            node_type = node_xml['type'] if node_xml.has_attr('type') else Node
            if node_type not in locals():
                raise Exception(f"<node />s type is not in scope: {node_xml}")

            node_cls = locals()[node_type]

            # TODO: Something doesn't feel correct here.
            # TODO: Determine if node does set_obj_inst or does the caller do it?!
            node = node_cls.from_xml(node_xml, ContextRef(result_ref))
            node_xml.set_obj_inst(node)

        # ** Note: If a user wants to explore what we've done, they can iterate
        # **       the XmlNode tree and call get_obj_inst for what we've processed.
        return pparse_xml


# TODO: This is a working class name. :(
class ResultRef:
    """A resolved reference to a result ID and its owning extraction.

    Constructed while processing a ``<result />`` XML element; looks up the
    corresponding ``BytesExtraction`` from the parent ``PparseXml`` and
    stores it for downstream use.

    Args:
        pparse_xml: The parent ``PparseXml`` that owns the result table.
        result_xml: The ``<result />`` XmlNode being processed.
    """


    def __init__(self, pparse_xml: PparseXml, result_xml: Any) -> None:
        self.pparse_xml = pparse_xml
        self.result_xml = result_xml
        result_ref_id = int(self.result_xml['id'])
        self.extraction = self.pparse_xml.get_extraction(result_ref_id)


# TODO: This is a working class name. :(
# This is weird because the parser creates the node and the node creates the context.
# therefore we want to create or track a parser and context arguments.
class ContextRef:
    """A bundle of the context needed when reconstructing a node from XML.

    Carries the ``ResultRef`` (which provides access to the extraction), the
    raw context XML element, and the resolved parser so that
    ``Node.from_xml`` does not need to resolve them itself.

    Args:
        result_ref: The ``ResultRef`` that connects this context to its
            extraction and ``PparseXml``.
        context_xml: The ``<context />`` XmlNode for this node, if present.
        parser: The ``Parser`` to use when rebuilding the node, if known.
    """


    def __init__(
        self, result_ref: ResultRef, context_xml: Optional[Any] = None, parser: Optional[Parser] = None
    ) -> None:
        self.result_ref = result_ref
        self.context_xml = context_xml
        self.parser = parser


from typing import Optional

from .reader import (
    Reader,
    Cursor,
)

# Generic artifact that ties parsers to cursor-ed data.
class Extraction:
    def __init__(self, name: str = None, source: Optional["Extraction"] = None):
        # The extraction we came from. Detect parser via source.
        self._source: Optional["Extraction"] = source
        self._name: Optional[str] = name  # name of extraction
        self._parser = {}  # parsers by id
        self._result = {}  # results by parser id
        self._extractions = []   # child extractions

    def name(self):
        return self._name

    def set_name(self, name):
        self._name = name
        return self


    # ! adding parser to an extraction is the old way of thinking. Now, we want to add a new
    # ! potential result tree.

    # At this point, caller has identified a parser for the extraction. The system now
    # needs to create a result slot that will contain the root node of the result and
    # the root node will hold the initial parser instance (which gets copied to all
    # relevant children).
    def add_result(self, id, root_node: Optional["Node"]):
        self._result[id] = root_node

    # TODO: Create passthrough load() for result or results

    def add_parser(self, id, parser: Optional["Parser"]):
        self._parser[id] = parser

    def has_parser(self, parser_id):
        return parser_id in self._parser

    def discover_parsers(self, parser_registry):
        for pname, parser in parser_registry.items():
            if not self.has_parser(pname):
                if parser.match_extension(self.name()):
                    self.add_parser(pname, parser(self, pname))
                    continue
                if parser.match_magic(self.open()):
                    self.add_parser(pname, parser(self, pname))
                    continue

        return self

    def open(self):
        raise NotImplementedError()

    # Process all data at once.
    # TODO: Parse data lazily.
    # TODO: What is the interface that only parses what we need to?
    def scan_data(self):
        for parser in self._parser.values():
            parser.scan_data()
        return self

    # extraction = Extraction.from_xml("<job />")
    @classmethod
    def from_xml(cls, xml_src, xml_root):
        raise NotImplementedError("from_xml not implemented")

    # extraction.to_xml() -> "<job />"
    def to_xml(self) -> str:
        raise NotImplementedError("to_xml not implemented")


# Generic artifact that ties parsers to cursor-ed data.
class BytesExtraction(Extraction):
    def __init__(
        self,
        name: str = None,
        source: Optional["Extraction"] = None,
        reader: Reader = None,
    ):
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

    def open(self):
        return self._reader.dup()

    def tell(self):
        return self._reader.tell()

    # extraction = Extraction.from_xml("<job />")
    @classmethod
    def from_xml(cls, xml_src, pparse_xml = None):

        from thirdparty.pparse._xml import XmlNode, XmlEntry
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

        # **Importing into locals**
        from thirdparty.pparse.lib import (
            FileData,
        )

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
                raise Exception(f"extraction must have a type attribute.")
            if child_extraction['type'] not in globals():
                raise Exception(f"child extraction type not in scope {child_extraction}")
            extraction_cls = globals()[child_extraction['type']]
            child_extraction.set_obj_inst(extraction_cls.from_xml(child_extraction, xml_root))

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
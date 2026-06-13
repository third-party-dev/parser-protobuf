import logging

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.xml.state import (
    XmlParsingBom,
    XmlParsingState,
)

def configure_pparser(**kwargs):

    class Parser(pparse.Parser):

        @staticmethod
        def match_extension(fname: str):
            if not fname:
                return False
            for ext in [".xml"]:
                if fname.endswith(ext):
                    return True
            return False


        @staticmethod
        def match_magic(cursor: pparse.Cursor):
            # TODO: Implement.
            return False


        def make_root_node(self, parent: pparse.Node = None, init_state = XmlParsingBom):

            init_state = self._init_state_as_cls(init_state)

            root = pparse.Node(self._source.open(), self, default_value = {}, parent = parent)
            root.ctx()._init_state(init_state)
            return root


        def __init__(self, source: pparse.Extraction, id: str = "zip"):
            super().__init__(source, id, XmlParsingState)

            self.encoding = "utf-8"
            self._max_char_size = 4


        def max_char_bytes(self, char_count):
            return char_count * self._max_char_size


        def decoded_peek(self, reader, char_count):
            return self.partial_decode(reader.peek(self.max_char_bytes(char_count)))


        @staticmethod
        def from_reader(reader: pparse.Reader):
            extraction = pparse.BytesExtraction(name="data.xml", reader=reader.dup())
            return Parser(extraction)


        def encoded_skip(self, reader, unicode_str):
            reader.skip(len(unicode_str.encode(self.encoding)))


        def encoded_len(self, unicode_str):
            # TODO: This feels wrong.
            return len(unicode_str.encode(self.encoding))

        def new_list_node(self, parent):
            return pparse.Node(parent.ctx().reader(), self, default_value = [], parent = parent)

        def new_map_node(self, parent):
            return pparse.Node(parent.ctx().reader(), self, default_value = {}, parent = parent)


        def new_data_node(self, parent):
            return pparse.Node(parent.ctx().reader(), self, parent = parent)


        def _end_container_node(self, node: pparse.Node):
            ctx = node.ctx()
            parent = ctx.parent()
            if parent:
                log.debug(f"end_container (off:{ctx.tell()}): Backtracking to parent.")

                # Set the end pointer to advance parent past field.
                ctx.mark_end(node)

                # Fast forward past the bit we just parsed.
                parent.ctx().seek(ctx._end)

        # extraction = Extraction.from_xml("<job />")
        @classmethod
        def from_xml(cls, source):
            from thirdparty.pparse._xml import XmlNode
            xml = XmlNode.as_node(source)

            # Do we have the correct node?
            # ** Assuming parser has type attribute.
            if xml.get_el().tag != "parser":
                raise Exception(f"Expected parser node. Got: {xml.get_el().tag}")
            if xml['type'] != "zip":
                raise Exception(f"Expected type zip parser. Got: {xml['type']}")
            
    return Parser

#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Iterator, Optional

import logging
log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.xml import configure_pparser

class Xml:
    def __init__(self) -> None:
        self._extraction: Optional[pparse.BytesExtraction] = None

    def _parse(self, data_source: Any, fname: str = "unnamed.xml", recursion: Optional[pparse.RecursionControl] = None) -> Xml:

        try:
            data_range = pparse.Range(data_source.open(), data_source.length)
            self._extraction = pparse.BytesExtraction(name=fname, reader=data_range)
            parser = configure_pparser()(self._extraction, 'xml')

            self._extraction.add_result('xml', parser.make_root_node())
            self._extraction._result['xml'].load(recursion=recursion)

        except pparse.EndOfDataException as e:
            print(e)
            pass
        except Exception as e:
            print(e)
            import traceback

            traceback.print_exc()

        return self


    def root_node(self) -> pparse.Node:
        return self._extraction._result['xml']


    def open_fpath(self, fpath: str, recursion: Optional[pparse.RecursionControl] = None) -> Xml:
        return self._parse(pparse.FileData(path=fpath), fname=fpath, recursion=recursion)


    def from_bytesio(self, bytes_io: Any, fname: str = "unnamed.xml", recursion: Optional[pparse.RecursionControl] = None) -> Xml:
        return self._parse(pparse.BytesIoData(bytes_io=bytes_io), fname=fname, recursion=recursion)


    def as_etree(self) -> ElementTree:
        from thirdparty.pparse.view.xml import ElementTree
        return ElementTree().from_pparse_node(self.root_node().value['document'], recursive=True)


# ! In real ElementTree, attribute name namespaces are expanded.

class Element:
    def __init__(self) -> None:
        self.clear()


    # resets an element, removes all sub-elements, clears all attributes, sets the text and tail attrs to None
    def clear(self) -> None:
        # element type (or tag)
        self.tag: str = ''
        # text before first child
        self.text: Optional[str] = None
        # text after closing tag, but inside parent.
        self.tail: Optional[str] = None

        # dictionary with element attributes
        self.attrib: dict[str, Any] = {}

        self._children: list[Element] = []  # list of children TODO: What is this member for real?!


    def from_pparse_node(self, node: Any, recursive: bool = False) -> Element:
        # Get tag
        self.tag = node.value['tag']


        # Get text
        if 'content' in node.value and len(node.value['content'].value) > 0 and \
            isinstance(node.value['content'].value[0].value, str):
            self.text = node.value['content'].value[0].value


            # Get tail
        if node.ctx() and node.ctx().parent() and node.ctx().parent():
            parent = node.ctx().parent()
            if 'content' in parent.value:
                try:

                    index = parent.value['content'].value.find(node)

                    if len(parent.value['content'].value) > index+1 and \
                        isinstance(parent.value['content'].value[index+1].value, str):
                        self.tail = parent.value['content'].value[index+1].value
                except:
                    breakpoint()

        # Get attribute dictionary
        self.attrib = node.value['attrib']

        if recursive:
            for child in node.value['content'].value:
                # Assuming child elements are dictionaries.
                if isinstance(child.value, dict) and 'tag' in child.value:
                    self._children.append(Element().from_pparse_node(child))

        return self


    # ---- Attributes Methods ----

    def get(self, attr: str, default: Any) -> Any:
        return self.attrib.get(attr, default)


    def items(self) -> Any:
        return self.attrib.items()


    def keys(self) -> Any:
        return self.attrib.keys()


    def set(self, attr: str, value: Any) -> Element:
        self.attrib[attr] = value
        return self


    # ---- Children Methods ----

    def append(self, element: Element) -> None:
        self._children.append(element)


    def extend(self, elements: list[Element]) -> None:
        self._children.extend(elements)


    def find(self, match: str, namespaces: Optional[Any] = None) -> Optional[Element]:
        if namespaces is not None:
            raise NotImplementedError("Namespaces not implemented in pparse xml find")
        if next((i for i, c in enumerate(match) if c in ['/','[']), -1) >= 0:
            raise NotImplementedError("Path matching not implemented in pparse xml find")

        return next(self.iterfind(match), None)


    def findall(self, match: str, namespaces: Optional[Any] = None) -> list[Element]:
        if namespaces is not None:
            raise NotImplementedError("Namespaces not implemented in pparse xml findall")
        if next((i for i, c in enumerate(match) if c in ['/','[']), -1) >= 0:
            raise NotImplementedError("Path matching not implemented in pparse xml findall")

        return list(self.iterfind(match))


    def findtext(self, match: str, default: Optional[str] = None, namespaces: Optional[Any] = None) -> Optional[str]:
        if namespaces is not None:
            raise NotImplementedError("Namespaces not implemented in pparse xml findtext")
        if next((i for i, c in enumerate(match) if c in ['/','[']), -1) >= 0:
            raise NotImplementedError("Path matching not implemented in pparse xml findtext")

        elem = self.find(match, namespaces)
        if elem is None:
            return default
        return elem.text or default


    def insert(self, index: int, subelement: Element) -> None:
        self._children.insert(index, subelement)


    def iter(self, tag: Optional[str] = None) -> Iterator[Element]:
        if tag is None or self.tag == tag:
            yield self
        for child in self._children:
            yield from child.iter(tag)


    def iterfind(self, match: str, namespaces: Optional[Any] = None) -> Iterator[Element]:
        if namespaces is not None:
            raise NotImplementedError("Namespaces not implemented in pparse xml iterfind")
        if next((i for i, c in enumerate(match) if c in ['/','[']), -1) >= 0:
            raise NotImplementedError("Path matching not implemented in pparse xml iterfind")

        if match == ".":
            yield self
        elif match == "*":
            yield from self._children
        yield from (c for c in self._children if c.tag == match)


    def makeelement(self, tag: str, attrib: dict[str, Any]) -> None:
        raise NotImplementedError("makeelement() not implemented in pparse xml")


    def remove(self, subelement: Element) -> None:
        self._children.remove(subelement)


    def __delitem__(self, item: Any) -> None:
        self.remove(item)


    def __getitem__(self, index: int) -> Element:
        return self._children[index]


    def __setitem__(self, index: int, value: Element) -> None:
        self._children[index] = value


    def __len__(self) -> int:
        return len(self._children)


class ElementTree:
    def __init__(self) -> None:
        self._root: Optional[Element] = None


    def from_pparse_node(self, node: Any, recursive: bool = False) -> ElementTree:
        self._setroot(Element().from_pparse_node(node, recursive=recursive))
        return self


    def _setroot(self, element: Element) -> None:
        self._root = element

    def find(self, match: str, namespaces: Optional[Any] = None) -> Optional[Element]:
        return self.getroot().find(match, namespaces=namespaces)

    def findall(self, match: str, namespaces: Optional[Any] = None) -> list[Element]:
        return self.getroot().findall(match, namespaces=namespaces)

    def findtext(self, match: str, default: Optional[Any] = None, namespaces: Optional[Any] = None) -> Optional[str]:
        return self.getroot().findtext(match, default=default, namespaces=namespaces)

    def getroot(self) -> Element:
        return self._root

    def iter(self, tag: Optional[str] = None) -> Iterator[Element]:
        return self.getroot().iter(tag)

    def iterfind(self, match: str, namespaces: Optional[Any] = None) -> None:
        self.getroot().iterfind(match, namespace=namespaces)

    def parse(source: Any, parser: Any = None) -> None:
        raise NotImplementedError("ElementTree.parse not implemented in pparse xml")

    def write(*args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("ElementTree.write not implemented in pparse xml")

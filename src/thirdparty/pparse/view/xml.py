#!/usr/bin/env python3

import logging
log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.xml import configure_pparser

class Xml:
    def __init__(self):
        self._extraction = None

    def _parse(self, data_source, fname="unnamed.xml", recursion=None):

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


    def root_node(self):
        return self._extraction._result['xml']


    def open_fpath(self, fpath, recursion=None):
        return self._parse(pparse.FileData(path=fpath), fname=fpath, recursion=recursion)


    def from_bytesio(self, bytes_io, fname="unnamed.xml", recursion=None):
        return self._parse(pparse.BytesIoData(bytes_io=bytes_io), fname=fname, recursion=recursion)


    def as_etree(self):
        from thirdparty.pparse.view.xml import ElementTree
        return ElementTree().from_pparse_node(self.root_node().value['document'], recursive=True)


# ! In real ElementTree, attribute name namespaces are expanded.

class Element:
    def __init__(self):
        self.clear()


    # resets an element, removes all sub-elements, clears all attributes, sets the text and tail attrs to None
    def clear(self):
        # element type (or tag)
        self.tag = ''
        # text before first child
        self.text = None 
        # text after closing tag, but inside parent.
        self.tail = None 

        # dictionary with element attributes 
        self.attrib = {}

        self._children = [] # list of children TODO: What is this member for real?!


    def from_pparse_node(self, node, recursive=False):
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

    def get(self, attr, default):
        return self.attrib.get(attr, default)


    def items(self):
        return self.attrib.items()


    def keys(self):
        return self.attrib.keys()


    def set(self, attr, value):
        self.attrib[attr] = value
        return self


    # ---- Children Methods ----

    def append(self, element):
        self._children.append(element)


    def extend(self, elements):
        self._children.extend(elements)


    def find(self, match, namespaces=None):
        if namespaces is not None:
            raise NotImplementedError("Namespaces not implemented in pparse xml find")
        if next((i for i, c in enumerate(match) if c in ['/','[']), -1) >= 0:
            raise NotImplementedError("Path matching not implemented in pparse xml find")

        return next(self.iterfind(match), None)


    def findall(self, match, namespaces=None):
        if namespaces is not None:
            raise NotImplementedError("Namespaces not implemented in pparse xml findall")
        if next((i for i, c in enumerate(match) if c in ['/','[']), -1) >= 0:
            raise NotImplementedError("Path matching not implemented in pparse xml findall")

        return list(self.iterfind(match))


    def findtext(self, match, default=None, namespaces=None):
        if namespaces is not None:
            raise NotImplementedError("Namespaces not implemented in pparse xml findtext")
        if next((i for i, c in enumerate(match) if c in ['/','[']), -1) >= 0:
            raise NotImplementedError("Path matching not implemented in pparse xml findtext")
        
        elem = self.find(match, namespaces)
        if elem is None:
            return default
        return elem.text or default


    def insert(self, index, subelement):
        self._children.insert(index, subelement)


    def iter(self, tag=None):
        if tag is None or self.tag == tag:
            yield self
        for child in self._children:
            yield from child.iter(tag)


    def iterfind(self, match, namespaces=None):
        if namespaces is not None:
            raise NotImplementedError("Namespaces not implemented in pparse xml iterfind")
        if next((i for i, c in enumerate(match) if c in ['/','[']), -1) >= 0:
            raise NotImplementedError("Path matching not implemented in pparse xml iterfind")
        
        if match == ".":
            yield self
        elif match == "*":
            yield from self._children
        yield from (c for c in self._children if c.tag == match)


    def makeelement(self, tag, attrib):
        raise NotImplementedError("makeelement() not implemented in pparse xml")


    def remove(self, subelement):
        self._children.remove(subelement)
    

    def __delitem__(self, item):
        self.remove(item)


    def __getitem__(self, index):
        return self._children[index]


    def __setitem__(self, index, value):
        self._children[index] = value


    def __len__(self):
        return len(self._children)


class ElementTree:
    def __init__(self):
        self._root = None


    def from_pparse_node(self, node, recursive=False):
        self._setroot(Element().from_pparse_node(node, recursive=recursive))
        return self


    def _setroot(self, element):
        self._root = element

    def find(self, match, namespaces=None):
        return self.getroot().find(match, namespaces=namespaces)
    
    def findall(self, match, namespaces=None):
        return self.getroot().findall(match, namespaces=namespaces)
    
    def findtext(self, match, default=None, namespaces=None):
        return self.getroot().findtext(match, default=default, namespaces=namespaces)
    
    def getroot(self) -> Element:
        return self._root

    def iter(self, tag=None):
        return self.getroot().iter(tag)

    def iterfind(self, match, namespaces=None):
        self.getroot().iterfind(match, namespace=namespaces)
    
    def parse(source, parser=None):
        raise NotImplementedError("ElementTree.parse not implemented in pparse xml")
    
    def write(*args, **kwargs):
        raise NotImplementedError("ElementTree.write not implemented in pparse xml")
# from xml.etree.ElementTree import Element, fromstring
# from typing import Optional
# from typing import Iterator


# class XmlNode:
#     # Use with `el = ElementTree.fromstring(source)`
#     def __init__(self, source: "str | Element"):
#         if isinstance(source, str):
#             self._el = fromstring(source)
#         else:
#             self._el = source

    


#     @classmethod
#     def as_node(cls, source: "str | Element | XmlNode") -> "XmlNode":
#         if isinstance(source, "XmlNode"):
#             return source
#         else:
#             return XmlNode(source)


#     # Given: <object><node /><node /><extra /></object>
#     # object.node[1] returns second <node>
#     def __getattr__(self, name: str) -> "XmlNode | list[XmlNode]":
#         children = self._el.findall(name)
#         if not children:
#             raise AttributeError(f"No child element '{name}'")
#         if len(children) == 1:
#             return XmlNode(children[0])
#         return [XmlNode(child) for child in children]


#     def __getitem__(self, key: str) -> str:
#         return self._el.attrib[key]


#     # `for child in parent`
#     def __iter__(self) -> Iterator["XmlNode"]:
#         return self.iter_all()


#     # Returns number of direct children.
#     def __len__(self) -> int:
#         return len(self._el)


#     # Returns the text value.
#     def __str__(self) -> str:
#         return self._el.text or ""


#     # Debug output
#     def __repr__(self) -> str:
#         attrs = " ".join(f'{k}="{v}"' for k, v in self._el.attrib.items())
#         return f"XmlNode<{self._el.tag}{' ' if len(attrs) else ''}{attrs}>"


#     # ----- `get_` prefix prevents shadowing children in __getattr__.

#     # # ** Note: probably cleaner to use str(node)
#     # @property
#     # def get_text(self) -> str:
#     #     return str(self)

#     # # ** Note: Probably cleaner to use node["attr_name"]
#     # @property
#     # def get_attr(self) -> dict:
#     #     return self._el.attrib

#     # # ** Note: Probably cleaner to use node.get_el().tag
#     # @property
#     # def get_tag(self) -> str:
#     #     return self._el.tag


#     # Return first element of name (use with hash maps)
#     def get(self, name: str) -> Optional["XmlNode"]:
#         child = self._el.find(name)
#         return XmlNode(child) if child is not None else None

#     # Return all elements or elements with name as generator (lazy).
#     def iter_all(self, name: Optional[str] = None) -> Iterator["XmlNode"]:
#         if name is None:
#             return (XmlNode(child) for child in self._el)
#         return (XmlNode(child) for child in self._el if child.tag == name)

#     # Return all elements or elements with name as list (eager).
#     def get_all(self, name: Optional[str] = None) -> "list[XmlNode]":
#         return list(self.iter_all(name))

#     # Return low level ElementTree object.
#     def get_el(self) -> Element:
#         return self._el














from __future__ import annotations

import json
from xml.etree.ElementTree import Element, fromstring
from typing import Any, Callable, Iterator, Optional, Union


class XmlNode:


    def __init__(self, source: Union[str, Element], parent: Optional[XmlNode] = None) -> None:
        self._obj_inst: Any = None
        self._el: Element = fromstring(source) if isinstance(source, str) else source
        self._parent: Optional[XmlNode] = parent
        self._children: dict[Element, XmlNode] = \
            {child: XmlNode(child, parent=self) for child in self._el}


    @classmethod
    def as_node(cls, source: Union[str, Element, XmlNode]) -> XmlNode:
        if isinstance(source, cls):
            return source
        else:
            return XmlNode(source)


    # Given: <object><node /><node /><extra /></object>
    # object.node returns XmlNode or list[XmlNode]
    def __getattr__(self, name: str) -> Union[XmlNode, list[XmlNode]]:
        children = [node for node in self._children.values() if node._el.tag == name]
        if not children:
            raise AttributeError(f"No child element '{name}'")
        if len(children) == 1:
            return children[0]
        return children


    # node["attr_name"] returns attribute value
    def __getitem__(self, key: str) -> str:
        return self._el.attrib[key]


    # `for child in parent`
    def __iter__(self) -> Iterator[XmlNode]:
        return self.iter_all()


    # Returns number of direct children.
    def __len__(self) -> int:
        return len(self._el)


    # Returns the text value.
    def __str__(self) -> str:
        return self._el.text or ""


    # Debug output
    def __repr__(self) -> str:
        attrs = " ".join(f'{k}="{v}"' for k, v in self._el.attrib.items())
        return f"XmlNode<{self._el.tag}{' ' if attrs else ''}{attrs}>"


    # Return parent node.
    def get_parent(self) -> Optional[XmlNode]:
        return self._parent


    # Return low level ElementTree object.
    def get_el(self) -> Element:
        return self._el


    def has_attr(self, attr: str) -> bool:
        return attr in self._el.attrib


    def has_tag(self, tag: str) -> bool:
        return self._el.tag == tag


    def set_obj_inst(self, obj: Any) -> Any:
        self._obj_inst = obj
        return obj


    def get_obj_inst(self) -> Any:
        return self._obj_inst


    # Return first child element of name, or None.
    def get(self, name: str) -> Optional[XmlNode]:
        return next((node for node in self._children.values() if node._el.tag == name), None)


    # Return all children or children with name as generator (lazy).
    def iter_all(self, name: Optional[str] = None) -> Iterator[XmlNode]:
        if name is None:
            return (node for node in self._children.values())
        return (node for node in self._children.values() if node._el.tag == name)


    # Return all children or children with name as list (eager).
    def get_all(self, name: Optional[str] = None) -> list[XmlNode]:
        return list(self.iter_all(name))
    
    # def get_linecol(self):
    #     return f"{self.get_el().sourceline}:{self.get_el().sourcecolumn}"

    
class XmlEntry:

    '''
      <extra>
        <entry type="int" name="offset">0</entry>
        <entry type="int" name="length">104857600</entry>
        <entry type="str" name="path">/etc/passwd</entry>
      </extra>

      implicitly becomes a map: {"offset": 0, "length": 104857600, "path": "/etc/passwd" }

      <configs>
        <entry type="list" name="extensions">
          <entry type="str">.txt</entry>
          <entry type="str">.json</entry>
        </entry>
        <entry type="str" name="msgtype">pparse</entry>
        <entry type="map" name="schema">
          <entry type="str" name="namespace">data</entry>
          <entry type="str" name="path">schema.json</entry>
        </entry>
      </configs>

      becomes:
        {
          "extensions": [ '.txt', '.json' ],
          "msgtype": pparse,
          "schema": { "namespace": "data", "path": "schema.json" }
        }
    '''


    # Note: We pass a node_cb so that _xml.py doesn't get caught up in import races.
    # Function for calling node callback.
    @staticmethod
    def as_node(node: XmlNode, node_cb: Optional[Callable[..., Any]] = None) -> Any:
        if not node_cb:
            raise Exception("<node /> found, but no handler defined.")
        # accepts <entry type="node /> and returns an instance of pparse.Node
        return node_cb(node)


    # Function for simple parsing (not recursion)
    @staticmethod
    def as_value(node: XmlNode) -> Any:
        if not node.has_attr("type") or node['type'] == 'str':
            return str(node).strip()
        if node['type'] == 'int':
            return int(str(node).strip())
        elif node['type'] == 'float':
            return float(str(node).strip())
        elif node['type'] == 'json':
            return json.loads(str(node).strip())


    # Function for using non-entry tag (e.g. node.value)
    @staticmethod
    def using(node: XmlNode, node_cb: Optional[Callable[..., Any]] = None) -> Any:
        if not node.has_attr('type') or node['type'] == 'map':
            # Implicitly a map.
            return XmlEntry.as_map(node, node_cb=node_cb)
        elif node['type'] == 'list':
            return XmlEntry.as_list(node, node_cb=node_cb)
        elif node['type'] == 'node':
            return XmlEntry.as_node(node, node_cb=node_cb)
        elif node['type'] in ['int', 'float', 'str', 'json']:
            return XmlEntry.as_value(node)
            

    '''
      <entry type="map" name="schema">
        <entry type="str" name="namespace">data</entry>
        <entry type="str" name="path">schema.json</entry>
      </entry>

      explicitly becomes map: { "namespace": "data", "path": "schema.json" }
    '''


    @staticmethod
    def as_map(node: XmlNode, obj: Optional[dict[str, Any]] = None, node_cb: Optional[Callable[..., Any]] = None) -> dict[str, Any]:
        obj = {} if obj is None else obj
        for entry in node.iter_all("entry"):
            if not entry.has_attr("name"):
                raise KeyError("entry is missing key value")
            name = entry['name']
            if name in obj:
                raise KeyError(f"duplicate entry name: {name}")
            
            if not entry.has_attr("type") or entry['type'] == 'str':
                obj[name] = str(entry).strip()
            elif entry['type'] == 'map':
                obj[name] = XmlEntry.as_map(entry, {}, node_cb=node_cb)
            elif entry['type'] == 'list':
                obj[name] = XmlEntry.as_list(entry, [], node_cb=node_cb)
            elif entry['type'] == 'node':
                obj[name] = XmlEntry.as_node(node, node_cb=node_cb)
            elif entry['type'] in ['int', 'float', 'str', 'json']:
                obj[name] = XmlEntry.as_value(entry)

            else:
                breakpoint()
                raise ValueError(f"Unknown entry type in map: {entry['type']}")
        return obj


    '''
      <entry type="list" name="extensions">
        <entry type="str">.txt</entry>
        <entry type="str">.json</entry>
      </entry>

      explicitly becomes list: [ '.txt', '.json' ]
    '''


    @staticmethod
    def as_list(node: XmlNode, obj: Optional[list[Any]] = None, node_cb: Optional[Callable[..., Any]] = None) -> list[Any]:
        obj = [] if obj is None else obj
        for entry in node.iter_all("entry"):
            if not entry.has_attr("type") or entry['type'] == 'str':
                obj.append(str(entry).strip())
            elif entry['type'] == 'map':
                obj.append(XmlEntry.as_map(entry, {}, node_cb=node_cb))
            elif entry['type'] == 'list':
                obj.append(XmlEntry.as_list(entry, [], node_cb=node_cb))
            elif entry['type'] == 'node':
                breakpoint()
                # ! Error: name undefined.
                #obj[name] = XmlEntry.as_node(node, node_cb=node_cb)
            elif entry['type'] in ['int', 'float', 'str', 'json']:
                obj.append(XmlEntry.as_value(entry))

            else:
                breakpoint()
                raise ValueError(f"Unknown entry type in list: {entry['type']}")
        return obj






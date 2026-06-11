
from __future__ import annotations

from typing import Any, Dict, Optional, Type, Union

from .extraction import (
    Extraction
)

"""
    Parser Considerations:

    It is the parser's responsibility to be lazy. The framework will allow a parser to
    attempt to scan over the data within its scope. The parser can choose to do all of
    the parsing in this phase, or ramain willfully ignorant of the data until the user
    references the data.

    It is difficult to anticipate the types of references that all interfaces would
    require. Therefore its also the parser's responsibility to implement the lookup
    API for the data within its scope. Parsers must use the framework's children member
    to advertise data that it is not willing or able to parse (e.g. another file within
    a zip container).

    It may be possible to implement an 80% solution API for referencing data in a generic
    way. The idea is that all data should be representable in a graph and you'd string
    together references to create a generic path to access any given information in the
    graph. In the generic data graph we'd have nodes that have children nodes and attributes.
    An API might resemble:

    - Node.parents() -> [Node] -> Return array of parents (strong refs).
    - Node.children() -> [weakref(Node)] -> Return array of childen (weak refs).
    - Triggers parse/load
    - Node.attributes() -> {} - Return dictionary of attributes.
    - Triggers parse/load
    - Node.child(index=-1) -> Node - Return strong ref child.
    - Triggers parse/load
    - Node.as_{bytes,i64,u64,str}() - Cast raw data as type.
    - Triggers parse/load
    - Node.loaded() - Is the data loaded and parsed?
    - Node.range() - A range of data this node covers.
    - Note: There could be situations where a conceptual "Node" is a non-continguous
            set of ranges in the data. Joining non-continguous sections of data into
            a cohesive object is not the responsibility of the parser or framework.
            That responsibility should fall to a higher level framework or code base.
    - Note: There should be nothing preventing nodes from overlapping. Its is the parsers
            responsibility to manage that situation and be aware that readahead
            optimizations will break when moving backward in memory.

    If all the child references were weakref. As long as there is a strong reference to
    the child, its path will remain.

    All nodes should be either in a loaded state or unloaded state. In the loaded state
    they are fully cached and dereference-able. In the unloaded state, the node is only
    a cursor into the data to be parsed.

    Note: When processing a large JSON object or array, all of the data needs to be
    read and parsed to know where the end of the object is and all of its immediate
    children.

    When scanning a file or Artifact, parse entire file to tracking size of:
    - What are the sizes of strings and serialized arrays of primatives?
    - What is the memory footprint of the data structure up to leaf nodes?
"""


# Base Parser for Extraction parsers.
class Parser:
    
    def __init__(self, source: Extraction, id: str, base_state_cls: Optional[Type[Any]] = None) -> None:
        if not isinstance(source, Extraction):
            raise TypeError("source must be an Extraction")

        # parser id
        # TODO: Shouldn't this be self known?
        self._id: str = id

        # parent source
        self._source = source

        # TODO: Store root node.
        # Current "Default" Node
        self.current = None

        # _all_states allows us to get a state class via a string name (in the context of a parser name)
        self._all_states = {}
        self._base_state_cls = None
        if base_state_cls:
            self._base_state_cls = base_state_cls
            def all_subclasses(base_cls):
                return base_cls.__subclasses__() + [s for sub in base_cls.__subclasses__() for s in all_subclasses(sub)]
            state_classes = all_subclasses(base_state_cls)
            for state in state_classes:
                self._all_states[state.__name__] = state


    def _init_state_as_cls(self, init_state: Union[str, Type[Any]]) -> Type[Any]:
        if isinstance(init_state, str):
            if init_state not in self._all_states:
                raise Exception(f"{self._base_state_cls.__name__} subclass given as string ({init_state}) is not in scope.")
            return self._all_states[init_state]

        if self._base_state_cls:
            if not isinstance(init_state, type):
                raise Exception(f"init_state parameter is not a class object.")
            if not issubclass(init_state, self._base_state_cls):
                raise Exception(f"Given state class ({init_state.__name__}) not a subclass of {self._base_state_cls.__name__}")

        return init_state


    def source(self) -> Extraction:
        return self._source

    # This processes all data at once.
    # TODO: What is the interface that only parses what we need to?
    def scan_data(self) -> None:
        raise NotImplementedError()

    @staticmethod
    def match_extension(fname: str) -> bool:
        return False

    @staticmethod
    def match_magic(cursor: Any) -> bool:
        return False




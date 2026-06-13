"""Base ``Parser`` class for format-specific extraction parsers."""

from __future__ import annotations

from typing import Any, Optional, Type, Union

from .extraction import (
    Extraction
)

"""
    Parser Considerations:

    It is the parser's responsibility to be lazy. The framework will allow a parser to
    attempt to scan over the data within its scope. The parser can choose to do all of
    the parsing in this phase, or remain willfully ignorant of the data until the user
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
    """Abstract base class for format-specific parsers attached to an ``Extraction``.

    A ``Parser`` is responsible for lazily interpreting the bytes provided by
    its ``Extraction`` and populating a tree of ``Node`` objects.  Concrete
    subclasses override ``match_extension`` and ``match_magic`` so the framework
    can auto-detect the right parser for a given data source.

    If ``base_state_cls`` is provided the constructor automatically discovers
    all transitive subclasses and registers them by name in ``_all_states``,
    enabling state lookup by string name via ``_init_state_as_cls``. (Required for
    XML load and resume.)

    Args:
        source: The ``Extraction`` this parser will consume.
        id: A unique string identifier for this parser within the extraction.
        base_state_cls: Optional base class for the parser's state machine.
            All subclasses of this class are registered in ``_all_states``.

    Raises:
        TypeError: If ``source`` is not an ``Extraction`` instance.
    """


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
        """Resolve ``init_state`` to a state class, validating it in the process.

        Accepts either a string name (looked up in ``_all_states``) or an
        actual class object (validated as a subclass of ``_base_state_cls``).
        (Required for XML load and resume.)

        Args:
            init_state: A state class or the string name of a registered state.

        Returns:
            The resolved state class.

        Raises:
            Exception: If a string name is not registered, if the argument is
                not a class object, or if the class is not a subclass of
                ``_base_state_cls``.
        """
        if isinstance(init_state, str):
            if init_state not in self._all_states:
                raise Exception(f"{self._base_state_cls.__name__} subclass given as string ({init_state}) is not in scope.")
            return self._all_states[init_state]

        if self._base_state_cls:
            if not isinstance(init_state, type):
                raise Exception("init_state parameter is not a class object.")
            if not issubclass(init_state, self._base_state_cls):
                raise Exception(f"Given state class ({init_state.__name__}) not a subclass of {self._base_state_cls.__name__}")

        return init_state


    def source(self) -> Extraction:
        """Return the ``Extraction`` this parser is consuming.

        Returns:
            The parent ``Extraction`` instance.
        """
        return self._source


    # This processes all data at once.
    # TODO: What is the interface that only parses what we need to?
    def scan_data(self) -> None:
        """Parse the entire data source eagerly, populating the node tree.

        Note: Legacy / Unused

        Raises:
            NotImplementedError: Must be implemented by each concrete subclass.
        """
        raise NotImplementedError()


    @staticmethod
    def match_extension(fname: str) -> bool:
        """Return whether the given filename suggests this parser can handle the data.

        Args:
            fname: The filename or path to test.

        Returns:
            ``True`` if the extension matches, ``False`` otherwise.
            The base implementation always returns ``False``.
        """
        return False


    @staticmethod
    def match_magic(cursor: Any) -> bool:
        """Return whether the magic bytes at the start of the data match this format.

        Args:
            cursor: A ``Reader`` positioned at the beginning of the data.

        Returns:
            ``True`` if the magic bytes match, ``False`` otherwise.
            The base implementation always returns ``False``.
        """
        return False




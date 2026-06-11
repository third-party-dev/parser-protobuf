from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Type

from .reader import (
    Reader,
    Range,
)

if TYPE_CHECKING:
    from .node import Node
    from .parser import Parser


class NodeContext:
    def __init__(self, parent: Optional[Node], reader: Reader, parser: Parser) -> None:
        self._reader = reader.dup()
        self._reader.seek(reader.tell())
        self._state_stack: List[Any] = []
        self._parent = parent  # Parent Node (None for root)
        self._start = self.tell()
        self._end: Optional[int] = None
        self._parser = parser
        # When doing a recursive parse, list of descendent references.
        self._descendants: List[Node] = []

    def parent(self) -> Optional[Node]:
        return self._parent

    def parent_ctx(self) -> Optional[NodeContext]:
        if self._parent:
            return self._parent.ctx()
        return None

    def reader(self) -> Reader:
        return self._reader.dup()

    def parser(self) -> Parser:
        return self._parser

    def _init_state(self, state: Type[Any]) -> None:
        self._state_stack = [state()]

    def _init_states(self, states: List[Type[Any]]) -> None:
        self._state_stack = [s() for s in reversed(states)]

    def _next_state(self, state: Type[Any]) -> None:
        # replace last state in stack
        # instantiate on insert so we can reuse members in state
        ## NEW WAY: self._state_stack[-1] = state()

        # TODO: Snippet to fix legacy code for now.
        # TODO: I'd prefer _init_state to eliminate condition.
        if self._state_stack:
            self._state_stack[-1] = state()
        else:
            self._state_stack.append(state())

    def _next_states(self, states: List[Type[Any]]) -> None:
        # _state_stack = [a, b, c]; _next_states([e, f, g]); _state_stack => [a, b, e, f, g]
        # extend state_stack with given states while removing the last element
        self._state_stack[-1:] = [s() for s in reversed(states)]



    # # push multiple states without removing current state
    # def _push_states(self, states):
    #     # instantiate on insert so we can reuse members in state
    #     self._state_stack.extend([s() for s in reversed(states)])

    def state(self) -> Any:
        # retrieve state instance
        return self._state_stack[-1]

    # caller expected to check _state_stack length too.
    def _pop_state(self) -> Any:
        if len(self._state_stack) > 1:
            # retrieve state instance
            return self._state_stack.pop()
        if len(self._state_stack) <= 0:
            raise Exception("Attempting to pop empty state stack.")
        # If caller intended to use last state, use state() method.
        raise Exception("Attempting to pop last state.")

    def set_remaining(self, length: int) -> None:
        self._end = self.tell() + length

    def mark_end(self, node: Node) -> None:
        self._end = self.tell()
        node.set_length(self._end - self._start)

    def mark_field_start(self) -> None:
        self._field_start = self.tell()

    def field_start(self) -> int:
        return self._field_start

    def dup(self) -> Reader:
        return self._reader.dup()

    def tell(self) -> int:
        return self._reader.tell()

    def seek(self, *args: Any, **kwargs: Any) -> Any:
        return self._reader.seek(*args, **kwargs)

    def skip(self, *args: Any, **kwargs: Any) -> Any:
        return self._reader.skip(*args, **kwargs)

    def peek(self, *args: Any, **kwargs: Any) -> bytes:
        return self._reader.peek(*args, **kwargs)

    def read(self, *args: Any, **kwargs: Any) -> bytes:
        return self._reader.read(*args, **kwargs)

    def left(self) -> int:
        if not isinstance(self._reader, Range):
            raise Exception("Reader must be range to use left()")
        return self._reader.left()

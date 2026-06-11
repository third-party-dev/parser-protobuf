"""NodeContext — per-node parser state machine and parser bookkeeping."""

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
    """Holds the parser state and reader position associated with a single ``Node``.

    ``NodeContext`` is the glue between a ``Node`` and its ``Parser``.  It
    owns the parser's state stack for the node and provides pass-through
    reader methods so that parser state objects do not need a direct
    reference to the underlying ``Reader``. It's also an all in one reference
    to cut once parsing is complete and we need to restore memory.

    Args:
        parent: The parent ``Node``, or ``None`` for the root.
        reader: The ``Reader`` positioned at the start of this node's data.
        parser: The ``Parser`` responsible for interpreting this node.
    """

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
        """Return the parent node of this context's node.

        Returns:
            The parent ``Node``, or ``None`` if this is the root node.
        """
        return self._parent

    def parent_ctx(self) -> Optional[NodeContext]:
        """Return the ``NodeContext`` of the parent node.

        Returns:
            The parent's ``NodeContext``, or ``None`` if there is no parent.
        """
        if self._parent:
            return self._parent.ctx()
        return None

    def reader(self) -> Reader:
        """Return an independent copy of the internal reader.

        Returns:
            A duplicated ``Reader`` at the current read position.
        """
        return self._reader.dup()

    def parser(self) -> Parser:
        """Return the parser associated with this context.

        Returns:
            The ``Parser`` instance for this node.
        """
        return self._parser

    def _init_state(self, state: Type[Any]) -> None:
        """Replace the entire state stack with a single initial state.

        Args:
            state: A state class (not an instance) to instantiate and push.
        """
        self._state_stack = [state()]

    def _init_states(self, states: List[Type[Any]]) -> None:
        """Replace the entire state stack with a sequence of initial states.

        States are provided in execution order; the first state in the list
        will be on top of the stack (processed first).

        Args:
            states: A list of state classes to instantiate.
        """
        self._state_stack = [s() for s in reversed(states)]

    def _next_state(self, state: Type[Any]) -> None:
        """Replace the top-of-stack state with a new state.

        If the stack is empty the new state is appended instead.

        Args:
            state: A state class (not an instance) to instantiate.
        """
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
        """Replace the top-of-stack state with a sequence of new states.

        Equivalent to popping the current top and pushing ``states`` in
        execution order.

        Args:
            states: A list of state classes to instantiate and push.
        """
        # _state_stack = [a, b, c]; _next_states([e, f, g]); _state_stack => [a, b, e, f, g]
        # extend state_stack with given states while removing the last element
        self._state_stack[-1:] = [s() for s in reversed(states)]



    # # push multiple states without removing current state
    # def _push_states(self, states):
    #     # instantiate on insert so we can reuse members in state
    #     self._state_stack.extend([s() for s in reversed(states)])

    def state(self) -> Any:
        """Return the current (top-of-stack) state instance.

        Returns:
            The active parser state object.
        """
        # retrieve state instance
        return self._state_stack[-1]

    # caller expected to check _state_stack length too.
    def _pop_state(self) -> Any:
        """Remove and return the top-of-stack state.

        The last remaining state can never be popped; use ``state()`` instead.

        Returns:
            The popped state instance.

        Raises:
            Exception: If the stack has only one element or is empty.
        """
        if len(self._state_stack) > 1:
            # retrieve state instance
            return self._state_stack.pop()
        if len(self._state_stack) <= 0:
            raise Exception("Attempting to pop empty state stack.")
        # If caller intended to use last state, use state() method.
        raise Exception("Attempting to pop last state.")

    def set_remaining(self, length: int) -> None:
        """Record the end of this node as ``current_position + length``.

        Args:
            length: Number of bytes remaining in the node from the current position.
        """
        self._end = self.tell() + length

    def mark_end(self, node: Node) -> None:
        """Record the current position as the end of the node and update its length.

        Args:
            node: The ``Node`` whose length should be set based on the bytes consumed.
        """
        self._end = self.tell()
        node.set_length(self._end - self._start)

    def mark_field_start(self) -> None:
        """Record the current read position as the start of the next field."""
        self._field_start = self.tell()

    def field_start(self) -> int:
        """Return the byte offset recorded by the most recent ``mark_field_start`` call.

        Returns:
            The saved field-start byte offset.
        """
        return self._field_start

    def dup(self) -> Reader:
        """Return an independent copy of the internal reader.

        Returns:
            A duplicated ``Reader`` at the current read position.
        """
        return self._reader.dup()

    def tell(self) -> int:
        """Return the current byte offset of the internal reader.

        Returns:
            The current read position.
        """
        return self._reader.tell()

    def seek(self, *args: Any, **kwargs: Any) -> Any:
        """Forward a seek call to the internal reader.

        Args:
            *args: Positional arguments forwarded to ``Reader.seek``.
            **kwargs: Keyword arguments forwarded to ``Reader.seek``.

        Returns:
            Whatever the underlying ``Reader.seek`` returns.
        """
        return self._reader.seek(*args, **kwargs)

    def skip(self, *args: Any, **kwargs: Any) -> Any:
        """Forward a skip call to the internal reader.

        Args:
            *args: Positional arguments forwarded to ``Reader.skip``.
            **kwargs: Keyword arguments forwarded to ``Reader.skip``.

        Returns:
            Whatever the underlying ``Reader.skip`` returns.
        """
        return self._reader.skip(*args, **kwargs)

    def peek(self, *args: Any, **kwargs: Any) -> bytes:
        """Forward a peek call to the internal reader.

        Args:
            *args: Positional arguments forwarded to ``Reader.peek``.
            **kwargs: Keyword arguments forwarded to ``Reader.peek``.

        Returns:
            Bytes read by the underlying ``Reader.peek``.
        """
        return self._reader.peek(*args, **kwargs)

    def read(self, *args: Any, **kwargs: Any) -> bytes:
        """Forward a read call to the internal reader.

        Args:
            *args: Positional arguments forwarded to ``Reader.read``.
            **kwargs: Keyword arguments forwarded to ``Reader.read``.

        Returns:
            Bytes read by the underlying ``Reader.read``.
        """
        return self._reader.read(*args, **kwargs)

    def left(self) -> int:
        """Return bytes remaining between the current position and the range end.

        The internal reader must be a ``Range`` for this to work.

        Returns:
            Number of bytes remaining in the range.

        Raises:
            Exception: If the internal reader is not a ``Range``.
        """
        if not isinstance(self._reader, Range):
            raise Exception("Reader must be range to use left()")
        return self._reader.left()

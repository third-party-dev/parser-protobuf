"""Reader interface and Cursor/Range implementations for binary data access."""

from __future__ import annotations
from typing import Any, Optional


# Api for Reader-like objects (Cursor, Range)
class Reader:
    """Abstract interface for objects that provide sequential and random access to binary data.

    Both ``Cursor`` and ``Range`` implement this interface.  Callers should
    program to ``Reader`` wherever possible so that either concrete type can
    be substituted transparently.
    """

    def dup(self) -> Reader:
        """Return an independent copy of this reader positioned at the same offset.

        Returns:
            A new ``Reader`` at the current position.
        """
        raise NotImplementedError()

    def tell(self) -> int:
        """Return the current absolute byte offset within the data source.

        Returns:
            The current read position as a byte offset.
        """
        raise NotImplementedError()

    def seek(self, offset: int) -> Any:
        """Move the read position to an absolute byte offset.

        Args:
            offset: Target byte offset within the data source.

        Returns:
            Implementation-defined; typically the resolved offset.
        """
        raise NotImplementedError()

    def skip(self, length: int) -> Any:
        """Advance the read position by ``length`` bytes without reading.

        Args:
            length: Number of bytes to skip forward.

        Returns:
            Implementation-defined; typically the new offset.
        """
        raise NotImplementedError()

    def peek(self, length: int) -> bytes:
        """Read ``length`` bytes starting at the current position without advancing.

        Args:
            length: Number of bytes to read.

        Returns:
            Up to ``length`` bytes of data.
        """
        raise NotImplementedError()

    def read(self, length: int) -> bytes:
        """Read ``length`` bytes and advance the read position accordingly.

        Args:
            length: Number of bytes to read.

        Returns:
            Up to ``length`` bytes of data.
        """
        raise NotImplementedError()


# Cursor manages offset. (Data does not manage offset.)
# Cursor does not manage boundaries.
class Cursor(Reader):
    """A stateful read pointer into a ``Data`` object.

    ``Cursor`` tracks the current byte offset and uses ``Data`` backend
    for all I/O access.  It does not enforce any boundary; that
    responsibility belongs to ``Range``.

    Args:
        data: The backing ``Data`` object that performs actual I/O.
        offset: Initial byte offset within ``data``.
    """

    def __init__(self, data: Any, offset: int = 0) -> None:
        self._data = data
        self._offset = offset

    def cursor(self) -> Cursor:
        """Return this cursor itself. (Maintains ignorance about Cursor vs Range.)

        Returns:
            ``self``.
        """
        return self

    def dup(self) -> Cursor:
        """Return a new ``Cursor`` at the current position by calling ``Data.open``.

        Returns:
            A new ``Cursor`` positioned at the current offset.
        """
        return self._data.open(self._offset)

    # Where in the Data are we
    def tell(self) -> int:
        """Return the current byte offset within the ``Data`` source.

        Returns:
            The current read position.
        """
        return self._offset

    # Set cursor to specific location.
    def seek(self, offset: int) -> Any:
        """Move this cursor to an absolute byte offset.

        Args:
            offset: Target byte offset.

        Returns:
            The value returned by the underlying ``Data.seek`` call.
        """
        self._offset = offset
        return self._data.seek(self)

    def skip(self, length: int) -> Any:
        """Advance this cursor by ``length`` bytes without reading any data.

        Args:
            length: Number of bytes to skip forward.

        Returns:
            The value returned by the underlying ``Data.seek`` call.
        """
        self._offset += length
        return self._data.seek(self)

    # Read data ahead without progressing cursor.
    def peek(self, length: int) -> bytes:
        """Read ``length`` bytes at the current position without advancing the cursor.

        Args:
            length: Number of bytes to read.

        Returns:
            Up to ``length`` bytes starting at the current offset.
        """
        return self._data.peek(self, length)

    # Copy and progress data.
    def read(self, length: int, mode: Any = None) -> bytes:
        """Read ``length`` bytes.

        Args:
            length: Max number of bytes to read.
            mode: Optional read mode hint passed to the backing data source.

        Returns:
            Up to ``length`` bytes of data.
        """
        data = self._data.read(self, length)
        self._offset += len(data)
        return data


# Range manages length and boundaries.
# Range start cursor and length are assumed correct.
# - Range has no insight into data.
# - Length must not be < 0
# Cursor does not manage length.
# Data does not manage offset.
class Range(Reader):
    """A bounded view over a region of a data source.

    ``Range`` wraps a ``Cursor`` and clamps all seek, skip, peek, and read
    operations to the half-open interval ``[start, start + length]``.  It
    does not duplicate any I/O logic — all actual data access is delegated
    to the underlying cursor.

    Args:
        cursor: A ``Cursor`` whose current position marks the start of the range.
        length: Number of bytes in the range.  Must be >= 0.
        offset: If >= 0, the initial read position within the range; otherwise
            defaults to the start of the range.

    Raises:
        ValueError: If ``length`` is negative.
    """

    # Given Cursor object is the start offset
    def __init__(self, cursor: Cursor, length: int, offset: int = -1) -> None:
        self._start_cursor = cursor.dup()
        self._init(cursor.tell(), length, offset)

    def _init(self, start_offset: int, length: int, current_offset: int = -1) -> None:
        """Initialise internal state from scalar offsets rather than a cursor object.

        Args:
            start_offset: Absolute byte offset at which the range begins.
            length: Number of bytes in the range.
            current_offset: Absolute byte offset for the initial read position.
                If negative the read position is set to ``start_offset``.

        Raises:
            ValueError: If ``length`` is negative.
        """
        self._start_cursor.seek(start_offset)
        self._start = self._start_cursor.tell()
        self._cursor = self._start_cursor.dup()

        if current_offset >= 0:
            self._cursor.seek(current_offset)
        if length < 0:
            raise ValueError("Length must not be < 0")
        # Consider: Check for length beyond data?
        self._length = length
        self._end = self._start + length

    def cursor(self) -> Cursor:
        """Return an independent copy of the internal read cursor.

        Returns:
            A duplicated ``Cursor`` at the current read position.
        """
        return self._cursor.dup()

    def dup(self) -> Range:
        """Return an independent copy of this range at the same read position.

        Returns:
            A new ``Range`` with the same bounds and current offset.
        """
        return Range(self._start_cursor, self._length, self._cursor.tell())

    def truncate(self, new_length: int) -> Range:
        """Shorten the range to ``new_length`` bytes.

        Args:
            new_length: The replacement length.  Must be <= the current length,
                and the current read position must not fall inside the truncated
                region.

        Returns:
            ``self``, to allow chaining.

        Raises:
            Exception: If ``new_length`` exceeds the current length.
            Exception: If the current cursor position would be inside the
                truncated region.
        """
        if new_length > self._length:
            raise Exception("Truncation of Range must be <= Range length")
        if self._cursor.tell() > self._start + new_length:
            raise Exception("Range cursor must not be in truncated space.")

        self._length = new_length
        self._end = self._start + self._length

        return self

    def length(self) -> int:
        """Return the total number of bytes in this range.

        Returns:
            The range length in bytes.
        """
        return self._length

    def left(self) -> int:
        """Return the number of bytes remaining between the cursor and the end of the range.

        Returns:
            Bytes available to read from the current position.
        """
        return self._end - self.tell()

    def valid_offset(self, offset: int) -> bool:
        """Return whether ``offset`` falls within ``[start, end]`` (inclusive).

        Args:
            offset: Absolute byte offset to test.

        Returns:
            ``True`` if the offset is within bounds, ``False`` otherwise.
        """
        return offset >= self._start and offset <= self._end

    def tell(self) -> int:
        """Return the current absolute byte offset of the internal cursor.

        Returns:
            The current read position.
        """
        return self._cursor.tell()

    # Set cursor to absolute location in Data (within bounds).
    def seek(self, offset: int) -> int:
        """Move the read position to an absolute offset, clamped to the range bounds.

        If ``offset`` is outside ``[start, end]`` it is clamped to the nearest
        boundary rather than raising an error.

        Args:
            offset: Target absolute byte offset.

        Returns:
            The (possibly clamped) offset that was actually ``seek``ed.
        """
        if not self.valid_offset(offset):
            if offset < self._start:
                offset = self._start
            elif offset > self._end:
                offset = self._end
        self._cursor.seek(offset)
        return offset

    # Ensure length (relative to cursor) is inbounds.
    def _adjust_length(self, length: int) -> int:
        """Clamp ``length`` so that reading it would not exceed the range end.

        Args:
            length: Requested number of bytes.

        Returns:
            The adjusted (clamped) byte count, guaranteed to be >= 0.
        """
        if length < 0:
            return 0
        offset = self.tell() + length
        if not self.valid_offset(offset):
            length = self._end - self.tell()
        return length

    # Progress data without reading.
    def skip(self, length: int) -> Any:
        """Advance the read position by up to ``length`` bytes, clamped to bounds.

        Args:
            length: Max number of bytes to skip forward.

        Returns:
            The value returned by the underlying cursor's skip call.
        """
        length = self._adjust_length(length)
        return self._cursor.skip(length)

    # Read data ahead without progressing cursor.
    def peek(self, length: int) -> bytes:
        """Read up to ``length`` bytes at the current position without advancing.

        The byte count is clamped so it does not exceed the range boundary.

        Args:
            length: Max number of bytes to read.

        Returns:
            Up to ``length`` bytes of data.
        """
        length = self._adjust_length(length)
        return self._cursor.peek(length)

    # Read data and progress data.
    def read(self, length: int) -> bytes:
        """Read up to ``length`` bytes.

        The byte count is clamped so it does not exceed the range boundary.

        Args:
            length: Max number of bytes to read.

        Returns:
            Up to ``length`` bytes of data.
        """
        length = self._adjust_length(length)
        return self._cursor.read(length)

from __future__ import annotations
from typing import Any


# Api for Reader-like objects (Cursor, Range)
class Reader:
    def dup(self) -> Reader:
        raise NotImplementedError()

    def tell(self) -> int:
        raise NotImplementedError()

    def seek(self, offset: int) -> Any:
        raise NotImplementedError()

    def skip(self, length: int) -> Any:
        raise NotImplementedError()

    def peek(self, length: int) -> bytes:
        raise NotImplementedError()

    def read(self, length: int) -> bytes:
        raise NotImplementedError()


# Cursor manages offset. (Data does not manage offset.)
# Cursor does not manage boundaries.
class Cursor(Reader):
    def __init__(self, data: Any, offset: int = 0) -> None:
        self._data = data
        self._offset = offset

    def cursor(self) -> Cursor:
        return self

    def dup(self) -> Cursor:
        return self._data.open(self._offset)

    # Where in the Data are we
    def tell(self) -> int:
        return self._offset

    # Set cursor to specific location.
    def seek(self, offset: int) -> Any:
        self._offset = offset
        return self._data.seek(self)

    def skip(self, length: int) -> Any:
        self._offset += length
        return self._data.seek(self)

    # Read data ahead without progressing cursor.
    def peek(self, length: int) -> bytes:
        return self._data.peek(self, length)

    # Copy and progress data.
    def read(self, length: int, mode: Any = None) -> bytes:
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
    # Given Cursor object is the start offset
    def __init__(self, cursor: Cursor, length: int, offset: int = -1) -> None:
        self._start_cursor = cursor.dup()
        self._init(cursor.tell(), length, offset)

    def _init(self, start_offset: int, length: int, current_offset: int = -1) -> None:
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
        return self._cursor.dup()

    def dup(self) -> Range:
        return Range(self._start_cursor, self._length, self._cursor.tell())

    def truncate(self, new_length: int) -> Range:
        if new_length > self._length:
            raise Exception("Truncation of Range must be <= Range length")
        if self._cursor.tell() > self._start + new_length:
            raise Exception("Range cursor must not be in truncated space.")

        self._length = new_length
        self._end = self._start + self._length

        return self

    def length(self) -> int:
        return self._length

    def left(self) -> int:
        return self._end - self.tell()

    def valid_offset(self, offset: int) -> bool:
        return offset >= self._start and offset <= self._end

    def tell(self) -> int:
        return self._cursor.tell()

    # Set cursor to absolute location in Data (within bounds).
    def seek(self, offset: int) -> int:
        if not self.valid_offset(offset):
            if offset < self._start:
                offset = self._start
            elif offset > self._end:
                offset = self._end
        self._cursor.seek(offset)
        return offset

    # Ensure length (relative to cursor) is inbounds.
    def _adjust_length(self, length: int) -> int:
        if length < 0:
            return 0
        offset = self.tell() + length
        if not self.valid_offset(offset):
            length = self._end - self.tell()
        return length

    # Progress data without reading.
    def skip(self, length: int) -> Any:
        length = self._adjust_length(length)
        return self._cursor.skip(length)

    # Read data ahead without progressing cursor.
    def peek(self, length: int) -> bytes:
        length = self._adjust_length(length)
        return self._cursor.peek(length)

    # Read data and progress data.
    def read(self, length: int) -> bytes:
        length = self._adjust_length(length)
        return self._cursor.read(length)

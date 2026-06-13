"""Exceptions raised by the pparse parsing framework."""


class EndOfDataException(Exception):
    """Raised when the end of the data currently available is reached."""

    pass


class EndOfNodeException(Exception):
    """Raised when the parser has finished processing the current node."""

    pass


class UnsupportedFormatException(Exception):
    """Raised when the observed data is not recognized by the parser."""

    pass


class BufferFullException(Exception):
    """Raised when a buffer cannot accept additional data."""

    pass

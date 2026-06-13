"""Abstract base class for tensor values parsed from binary model formats."""

from __future__ import annotations

from typing import Any, List

import numpy


class Tensor:
    """Abstract representation of a typed, shaped tensor stored in a binary format.

    Subclasses are expected to implement all abstract methods to provide
    access to the underlying data in a format-independent way.  The class
    also provides lookup tables that map pparse dtype strings to struct
    format characters, element sizes, and NumPy dtypes.
    """

    STTYPE_STRUCT = {
        "I8": "b",
        "U8": "B",
        "I16": "h",
        "U16": "H",
        "I32": "i",
        "U32": "I",
        "I64": "q",
        "U64": "Q",
        "F32": "f",
        "F64": "d",
    }

    STTYPE_SIZE = {
        "I8": 1,
        "U8": 1,
        "I16": 2,
        "U16": 2,
        "I32": 4,
        "U32": 4,
        "I64": 8,
        "U64": 8,
        "F32": 4,
        "F64": 8,
    }

    STTYPE_NP_MAP = {
        "F32": numpy.float32,
        "F64": numpy.float64,
        "F16": numpy.float16,
        # ! TypeError: data type 'bfloat16' not understood
        #'BF16': numpy.dtype("bfloat16"),
        "I8": numpy.int8,
        "I16": numpy.int16,
        "I32": numpy.int32,
        "I64": numpy.int64,
        "U8": numpy.uint8,
        "BOOL": numpy.bool_,
    }


    # Return (safetensors equivalent) type
    def get_type(self) -> str:
        """Return the safetensors-compatible dtype string for this tensor.

        Returns:
            A dtype string such as ``"F32"``, ``"I64"``, etc.
        """
        raise NotImplementedError()


    # Return (safetensors equivalent) shape
    def get_shape(self) -> List[int]:
        """Return the safetensors-compatible shape of this tensor.

        Returns:
            A list of dimension sizes, e.g. ``[batch, channels, height, width]``.
        """
        raise NotImplementedError()


    # Return raw data as extracted from source
    def get_data_bytes(self) -> bytes:
        """Return the raw tensor data exactly as it appears in the source.

        Returns:
            The raw byte content of the tensor.
        """
        raise NotImplementedError()


    # Return raw data as python array of dtype
    def as_array(self) -> Any:
        """Return the tensor data as a Python array typed to the tensor's dtype.

        Returns:
            A Python sequence or array object representing the tensor values.
        """
        raise NotImplementedError()


    # Return raw data as numpy array of dtype
    def as_numpy(self) -> numpy.ndarray:
        """Return the tensor data as a NumPy array typed to the tensor's dtype and shape.

        Returns:
            A ``numpy.ndarray`` with the appropriate dtype and shape.
        """
        raise NotImplementedError()

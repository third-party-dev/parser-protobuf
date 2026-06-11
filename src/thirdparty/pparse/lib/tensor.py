from __future__ import annotations

from typing import Any, List

import numpy


class Tensor:
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
        raise NotImplementedError()

    # Return (safetensors equivalent) shape
    def get_shape(self) -> List[int]:
        raise NotImplementedError()

    # Return raw data as extracted from source
    def get_data_bytes(self) -> bytes:
        raise NotImplementedError()

    # Return raw data as python array of dtype
    def as_array(self) -> Any:
        raise NotImplementedError()

    # Return raw data as numpy array of dtype
    def as_numpy(self) -> numpy.ndarray:
        raise NotImplementedError()

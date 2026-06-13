from __future__ import annotations

from typing import Optional

import numpy

class OnnxDataType:
    UNDEFINED: int = 0
    FLOAT: int = 1
    UINT8: int = 2
    INT8: int = 3
    UINT16: int = 4
    INT16: int = 5
    INT32: int = 6
    INT64: int = 7
    STRING: int = 8
    BOOL: int = 9
    FLOAT16: int = 10
    DOUBLE: int = 11
    UINT32: int = 12
    UINT64: int = 13
    COMPLEX64: int = 14
    COMPLEX128: int = 15
    BFLOAT16: int = 16
    FLOAT8E4M3FN: int = 17
    FLOAT8E4M3FNUZ: int = 18
    FLOAT8E5M2: int = 19
    FLOAT8E5M2FNUZ: int = 20
    UINT4: int = 21
    INT4: int = 22
    FLOAT4E2M1: int = 23
    FLOAT8E8M0: int = 24

    STTYPES: dict[int, str] = {
        UNDEFINED: "UNK",
        FLOAT: "F32",
        UINT8: "U8",
        INT8: "I8",
        UINT16: "U16",
        INT16: "I16",
        INT32: "I32",
        INT64: "I64",
        STRING: "UNK",
        BOOL: "BOOL",
        FLOAT16: "F16",
        DOUBLE: "F64",
        INT32: "U32",
        UINT64: "U64",
        COMPLEX64: "UNK",
        COMPLEX128: "UNK",
        BFLOAT16: "BF16",
        FLOAT8E4M3FN: "UNK",
        FLOAT8E4M3FNUZ: "UNK",
        FLOAT8E5M2: "UNK",
        FLOAT8E5M2FNUZ: "UNK",
        UINT4: "UNK",
        INT4: "UNK",
        FLOAT4E2M1: "UNK",
        FLOAT8E8M0: "UNK",
    }

    NPTYPES: dict[int, Optional[type]] = {
        UNDEFINED: None,
        FLOAT: numpy.float32,
        UINT8: numpy.uint8,
        INT8: numpy.int8,
        UINT16: numpy.uint16,
        INT16: numpy.int16,
        INT32: numpy.int32,
        INT64: numpy.int64,
        STRING: None,
        BOOL: numpy.bool_,
        FLOAT16: numpy.float16,
        DOUBLE: numpy.float64,
        UINT32: numpy.uint32,
        UINT64: numpy.uint64,
        COMPLEX64: numpy.complex64,
        COMPLEX128: numpy.complex128,
        BFLOAT16: None, #numpy.dtype("bfloat16"),
        FLOAT8E4M3FN: None,
        FLOAT8E4M3FNUZ: None,
        FLOAT8E5M2: None,
        FLOAT8E5M2FNUZ: None,
        UINT4: None,
        INT4: None,
        FLOAT4E2M1: None,
        FLOAT8E8M0: None,
    }

    def sttype(onnx_type: int) -> str:
        if onnx_type in OnnxDataType.STTYPES:
            return OnnxDataType.STTYPES[onnx_type]
        else:
            return "UNK"

    def nptype(onnx_type: int) -> Optional[type]:
        if onnx_type in OnnxDataType.NPTYPES:
            return OnnxDataType.NPTYPES[onnx_type]
        else:
            return None



'''
    enum DataType {
        UNDEFINED = 0;
        // Basic types.
        FLOAT = 1;   // float
        UINT8 = 2;   // uint8_t
        INT8 = 3;    // int8_t
        UINT16 = 4;  // uint16_t
        INT16 = 5;   // int16_t
        INT32 = 6;   // int32_t
        INT64 = 7;   // int64_t
        STRING = 8;  // string
        BOOL = 9;    // bool

        // IEEE754 half-precision floating-point format (16 bits wide).
        // This format has 1 sign bit, 5 exponent bits, and 10 mantissa bits.
        FLOAT16 = 10;

        DOUBLE = 11;
        UINT32 = 12;
        UINT64 = 13;
        COMPLEX64 = 14;     // complex with float32 real and imaginary components
        COMPLEX128 = 15;    // complex with float64 real and imaginary components

        // Non-IEEE floating-point format based on IEEE754 single-precision
        // floating-point number truncated to 16 bits.
        // This format has 1 sign bit, 8 exponent bits, and 7 mantissa bits.
        BFLOAT16 = 16;

        // Non-IEEE floating-point format based on papers
        // FP8 Formats for Deep Learning, https://arxiv.org/abs/2209.05433,
        // 8-bit Numerical Formats For Deep Neural Networks, https://arxiv.org/pdf/2206.02915.pdf.
        // Operators supported FP8 are Cast, CastLike, QuantizeLinear, DequantizeLinear.
        // The computation usually happens inside a block quantize / dequantize
        // fused by the runtime.
        FLOAT8E4M3FN = 17;    // float 8, mostly used for coefficients, supports nan, not inf
        FLOAT8E4M3FNUZ = 18;  // float 8, mostly used for coefficients, supports nan, not inf, no negative zero
        FLOAT8E5M2 = 19;      // follows IEEE 754, supports nan, inf, mostly used for gradients
        FLOAT8E5M2FNUZ = 20;  // follows IEEE 754, supports nan, not inf, mostly used for gradients, no negative zero

        // 4-bit integer data types
        UINT4 = 21;  // Unsigned integer in range [0, 15]
        INT4 = 22;   // Signed integer in range [-8, 7], using two's-complement representation

        // 4-bit floating point data types
        FLOAT4E2M1 = 23;

        // E8M0 type used as the scale for microscaling (MX) formats:
        // https://www.opencompute.org/documents/ocp-microscaling-formats-mx-v1-0-spec-final-pdf
        FLOAT8E8M0 = 24;

        // Future extensions go here.
    }
'''
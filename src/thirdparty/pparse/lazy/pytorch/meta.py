from __future__ import annotations


class PT:
    PKL_STTYPE_MAP: dict[str, str] = {
        "torch.FloatStorage": "F32",
        "torch.DoubleStorage": "F64",
        "torch.HalfStorage": "F16",
        "torch.BFloat16Storage": "BF16",
        "torch.CharStorage": "I8",
        "torch.ShortStorage": "I16",
        "torch.IntStorage": "I32",
        "torch.LongStorage": "I64",
        "torch.ByteStorage": "U8",
        "torch.BoolStorage": "BOOL",
        # # Unknown safetensor equivalency.
        # 'ComplexFloatStorage': '',
        # 'ComplexDoubleStorage': '',
        # # Map guessed based on np equivalency
        # 'QInt8Storage': 'I8',
        # 'QUInt8Storage': 'U8',
        # 'QInt32Storage': 'I32',
    }

    PERSID_CALL: int = 0

    TYPE_TAG: int = 0
    TYPE_NAME: int = 1
    DATA_KEY: int = 2
    DATA_DEST: int = 3
    ELEM_CNT: int = 4
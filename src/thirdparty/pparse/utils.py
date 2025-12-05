import io
import pathlib

import logging
log = logging.getLogger(__name__)

def has_mmap():
    try:
        import mmap
    except:
        return None

    try:
        with mmap.mmap(-1, 1) as m:
            m[0] = b"x"[0]
    except:
        return None
    
    return mmap

mmap = has_mmap()

def hexdump(data, length=None):
    if isinstance(data, io.BytesIO):
        data = data.getvalue()

    if length is None:
        length = len(data)
    data = data[:length]

    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join(f'{byte:02x}' for byte in chunk)
        ascii_part = ''.join(chr(byte) if 32 <= byte <= 126 else '.' for byte in chunk)
        print(f'{i:08x}: {hex_part:<47}  {ascii_part}')

def find_project_root(start: pathlib.Path = None) -> pathlib.Path:
    if start is None:
        start = pathlib.Path(__file__).resolve()
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise FileNotFoundError("pyproject.toml not found.")


def pparse_repr(obj, depth = 0, step = '  '):
    res = []

    if hasattr(obj, "pparse_repr"):
        res.append(obj.pparse_repr(depth, step))

    elif isinstance(obj, dict):
        dict_spacer = depth * step
        res.append('{\n')

        # Assuming key is always string or scalar
        key_spacer = (depth + 1) * step
        for k, v in obj.items():
            if hasattr(v, "pparse_repr"):
                res.append(f'{key_spacer}{k}: {v.pparse_repr(depth+1, step)}\n')
            else:
                res.append(f'{key_spacer}{k}: {pparse_repr(v, depth+1, step)}')

        res.append(dict_spacer + '}\n')

    elif isinstance(obj, (list, tuple, set)):
        itr_spacer = depth * step
        res.append('[\n')

        elem_spacer = (depth + 1) * step
        for elem in obj:
            if hasattr(elem, "pparse_repr"):
                res.append(f'{elem_spacer}{elem.pparse_repr(depth+1, step)}\n')
            else:
                res.append(f'{elem_spacer}{pparse_repr(elem, depth+1, step)}')

        res.append(itr_spacer + ']\n')
    
    else:
        res.append(f'{obj}\n')

    return ''.join(res)

from __future__ import annotations

import io
import sys
import logging
import pathlib
from typing import Any, Optional

class ListType:
    MIXED: int = 0
    UBYTE: int = 1
    BYTE: int = 2
    INT: int = 3
    FLOAT: int = 4

log = logging.getLogger(__name__)

def activate_logging(args: Any) -> None:
    level = {
        0: logging.ERROR,
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.DEBUG,
    }.get(args.verbose, logging.DEBUG)

    logging.basicConfig(level=level, format="%(levelname)-8s %(name)s: %(message)s")

    for spec in args.log_level:
        module, level_name = spec.split(":")
        logging.getLogger(module).setLevel(getattr(logging, level_name.upper()))


def has_mmap() -> Any:
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


def hexdump(data: Any, length: Optional[int] = None) -> None:
    if isinstance(data, io.BytesIO):
        data = data.getvalue()

    if length is None:
        length = len(data)
    data = data[:length]

    for i in range(0, len(data), 16):
        chunk = data[i : i + 16]
        hex_part = " ".join(f"{byte:02x}" for byte in chunk)
        ascii_part = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
        print(f"{i:08x}: {hex_part:<47}  {ascii_part}")


def find_project_root(start: Optional[pathlib.Path] = None) -> pathlib.Path:
    if start is None:
        start = pathlib.Path(__file__).resolve()
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise FileNotFoundError("pyproject.toml not found.")


def pparse_repr(obj: Any, depth: int = 0, step: str = "  ") -> str:
    res = []

    if hasattr(obj, "pparse_repr"):
        res.append(obj.pparse_repr(depth, step))

    elif isinstance(obj, dict):
        dict_spacer = depth * step
        res.append("{\n")

        # Assuming key is always string or scalar
        key_spacer = (depth + 1) * step
        for k, v in obj.items():
            if hasattr(v, "pparse_repr"):
                res.append(f"{key_spacer}{k}: {v.pparse_repr(depth + 1, step)}\n")
            else:
                res.append(f"{key_spacer}{k}: {pparse_repr(v, depth + 1, step)}")

        res.append(dict_spacer + "}\n")

    elif isinstance(obj, (list, tuple, set)):
        itr_spacer = depth * step
        res.append("[\n")

        elem_spacer = (depth + 1) * step
        for elem in obj:
            if hasattr(elem, "pparse_repr"):
                res.append(f"{elem_spacer}{elem.pparse_repr(depth + 1, step)}\n")
            else:
                res.append(f"{elem_spacer}{pparse_repr(elem, depth + 1, step)}")

        res.append(itr_spacer + "]\n")

    else:
        res.append(f"{obj}\n")

    return "".join(res)


def run_test_independently(caller_log: Any, test_calls: list[Any]) -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog=sys.argv[0])
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("--log-level", metavar="MODULE:LEVEL", action="append", default=[])
    parser.add_argument("--breakpoint", dest="breakpoint", action="store_true")

    cli_args = parser.parse_args()
    activate_logging(cli_args)

    for fn, args, kwargs in test_calls:
        fn(*(args or []), **(kwargs or {}))

    if cli_args.breakpoint:
        breakpoint()


def decode_utf8_partial(data: bytes) -> tuple[str, int]:
    # Easy path
    try:
        return data.decode("utf-8"), len(data)
    except UnicodeDecodeError:
        pass

    # Binary-search for the longest valid UTF-8 slice
    lo, hi = 0, len(data)
    tmp = None
    while lo < hi:
        mid = (lo + hi + 1) // 2
        try:
            tmp = data[:mid].decode("utf-8")
            lo = mid
        except UnicodeDecodeError:
            hi = mid - 1

    return (tmp if tmp is not None else ""), lo
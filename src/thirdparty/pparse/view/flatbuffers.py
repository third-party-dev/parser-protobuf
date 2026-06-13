#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Optional

import logging

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.flatbuffers import make_flatbuffers_parser


class Flatbuffers:


    def __init__(self) -> None:
        self._extraction: Optional[pparse.BytesExtraction] = None


    def _parse(
        self,
        data_source: Any,
        json_schema_path: str,
        fname: str = "unnamed.flatbuffers.bin",
        recursion: Optional[pparse.RecursionControl] = None,
    ) -> Flatbuffers:

        import json
        from pathlib import Path

        with open(json_schema_path, "r") as fobj:
            json_schema = json.loads(fobj.read())

        try:
            data_range = pparse.Range(data_source.open(), data_source.length)
            self._extraction = pparse.BytesExtraction(name=fname, reader=data_range)

            parser_class = make_flatbuffers_parser(ext_list=[Path(fname).suffix], json_schema=json_schema)
            parser = parser_class(self._extraction, 'flatbuffers')

            self._extraction.add_result('flatbuffers', parser.make_root_node())
            self._extraction._result['flatbuffers'].load(recursion=recursion)

            # self._extraction.add_parser('flatbuffers', parser)
            # self._extraction.discover_parsers({"flatbuffers": parser})
            # self._extraction._parser['flatbuffers']._root.load(recursion=recursion)

        except pparse.EndOfDataException as e:
            print(e)
            pass
        except Exception as e:
            print(e)
            import traceback

            traceback.print_exc()

        return self


    def root_node(self) -> pparse.Node:
        return self._extraction._result['flatbuffers']


    def open_fpath(
        self, fpath: str, json_schema_path: str, recursion: Optional[pparse.RecursionControl] = None
    ) -> Flatbuffers:
        return self._parse(pparse.FileData(path=fpath), json_schema_path, fname=fpath, recursion=recursion)


    def from_bytesio(
        self,
        bytes_io: Any,
        json_schema_path: str,
        fname: str = "unnamed.flatbuffers.bin",
        recursion: Optional[pparse.RecursionControl] = None,
    ) -> Flatbuffers:
        return self._parse(pparse.BytesIoData(bytes_io=bytes_io), json_schema_path, fname=fname, recursion=recursion)

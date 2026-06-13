#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Optional

import logging

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.protobuf import configure_pparser
from thirdparty.pparse.lazy.protobuf.meta import PbImport


class Parser:


    def __init__(self) -> None:
        self._extraction: Optional[pparse.BytesExtraction] = None


    def _parse(
        self,
        data_source: Any,
        pbpath: Any,
        msgtype: str,
        fname: str = "unnamed.protobuf.bin",
        recursion: Optional[pparse.RecursionControl] = None,
    ) -> Parser:

        from pathlib import Path

        try:
            data_range = pparse.Range(data_source.open(), data_source.length)
            self._extraction = pparse.BytesExtraction(name=fname, reader=data_range)
            parser_class = configure_pparser(
                ext_list=[Path(fname).suffix], init_msgtype=msgtype, proto=PbImport(pbpath)
            )
            parser = parser_class(self._extraction, 'protobuf')

            self._extraction.add_result('protobuf', parser.make_root_node())
            self._extraction._result['protobuf'].load(recursion=recursion)

            # self._extraction.add_parser('protobuf', parser)
            # self._extraction.discover_parsers({"protobuf": parser})
            # self._extraction._parser['protobuf']._root.load(recursion=recursion)

        except pparse.EndOfDataException as e:
            print(e)
            pass
        except Exception as e:
            print(e)
            import traceback

            traceback.print_exc()

        return self


    def root_node(self) -> pparse.Node:
        return self._extraction._result['protobuf']


    def open_fpath(
        self, fpath: str, pbpath: Any, msgtype: str, recursion: Optional[pparse.RecursionControl] = None
    ) -> Parser:
        return self._parse(pparse.FileData(path=fpath), pbpath, msgtype, fname=fpath, recursion=recursion)


    def from_bytesio(
        self,
        bytes_io: Any,
        pbpath: Any,
        msgtype: str,
        fname: str = "unnamed.protobuf.bin",
        recursion: Optional[pparse.RecursionControl] = None,
    ) -> Parser:
        return self._parse(pparse.BytesIoData(bytes_io=bytes_io), pbpath, msgtype, fname=fname, recursion=recursion)

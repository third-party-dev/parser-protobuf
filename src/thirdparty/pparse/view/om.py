#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Optional

import logging

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
#from thirdparty.pparse.lazy.protobuf.meta import PbImport
from thirdparty.pparse.lazy.om import configure_pparser

class Om:
    def __init__(self) -> None:
        self._extraction: Optional[pparse.BytesExtraction] = None


    def _parse(self, data_source: Any, recursion: Optional[pparse.RecursionControl] = None, header_only: bool = False, fname: str = "unnamed.om") -> Om:
        try:
            log.info("Parsing the OM container file.")
            data_range = pparse.Range(data_source.open(), data_source.length)
            self._extraction = pparse.BytesExtraction(name=fname, reader=data_range)
            parser = configure_pparser()(self._extraction, 'om')
            self._extraction.add_result('om', parser.make_root_node())
            self._extraction._result['om'].load(recursion=recursion)

            #self._extraction.add_parser('om', parser)
            #self._extraction._parser['om']._root.load(recursion=recursion)

        except pparse.EndOfDataException as e:
            print(e)
            pass
        except Exception as e:
            print(e)
            import traceback

            traceback.print_exc()

        return self


    def root_node(self) -> pparse.Node:
        return self._extraction._result['om']


    def open_fpath(self, fpath: str, recursion: Optional[pparse.RecursionControl] = None, header_only: bool = False) -> Om:
        return self._parse(pparse.FileData(path=fpath), recursion=recursion, header_only=header_only, fname=fpath)


    def from_bytesio(self, bytes_io: Any, recursion: Optional[pparse.RecursionControl] = None, header_only: bool = False, fname: str = "unnamed.om") -> Om:
        return self._parse(pparse.BytesIoData(bytes_io=bytes_io), recursion=recursion, header_only=header_only, fname=fname)

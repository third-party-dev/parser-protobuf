#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Optional

import logging

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.pickle import configure_pparser

class Pickle:


    def _parse(self, data_source: Any, fname: str = "unnamed.pkl", recursion: Optional[pparse.RecursionControl] = None) -> Pickle:
        self._extraction: Optional[pparse.BytesExtraction]

        try:
            data_range = pparse.Range(data_source.open(), data_source.length)
            self._extraction = pparse.BytesExtraction(name=fname, reader=data_range)
            parser = configure_pparser()(self._extraction, 'pkl')

            self._extraction.add_result('pkl', parser.make_root_node())
            self._extraction._result['pkl'].load(recursion=recursion)

            #self._extraction.add_parser('pkl', parser)
            #self._extraction.discover_parsers({"pkl": LazyPickleParser})
            #self._extraction._parser['pkl']._root.load(recursion=recursion)

        except pparse.EndOfDataException as e:
            print(e)
            pass
        except Exception as e:
            print(e)
            import traceback

            traceback.print_exc()

        return self


    def root_node(self) -> pparse.Node:
        return self._extraction._result['pkl']


    def open_fpath(self, fpath: str, recursion: Optional[pparse.RecursionControl] = None) -> Pickle:
        return self._parse(pparse.FileData(path=fpath), fname=fpath, recursion=recursion)


    def from_bytesio(self, bytes_io: Any, fname: str = "unnamed.pkl", recursion: Optional[pparse.RecursionControl] = None) -> Pickle:
        return self._parse(pparse.BytesIoData(bytes_io=bytes_io), fname=fname, recursion=recursion)

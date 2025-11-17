#!/usr/bin/env python3

import os
import struct

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.protobuf import Parser as LazyProtobufParser


class Onnx():
    PARSER_REGISTRY = {
        'protobuf': LazyProtobufParser,
    }


    def __init__(self):
        self._extraction = None


    def open_fpath(self, fpath):

        try:
            data_source = pparse.Data(path=fpath)
            data_range = pparse.Range(data_source.open(), data_source.length)
            self._extraction = pparse.Extraction(reader=data_range, name=fpath)
            self._extraction.discover_parsers(Onnx.PARSER_REGISTRY)
            self._extraction.scan_data()
        except pparse.EndOfDataException as e:
            print(e)
            pass
        except Exception as e:
            print(e)
            import traceback
            traceback.print_exc()

        return self




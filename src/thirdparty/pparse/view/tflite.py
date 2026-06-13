#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Optional

import logging
log = logging.getLogger(__name__)

import struct
import numpy

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.flatbuffers import configure_pparser


class Tensor(pparse.Tensor):

    # TFlite3 Tensor Types
    FLOAT32: int = 0     #
    FLOAT16: int = 1     # not supported
    INT32: int = 2       #
    UINT8: int = 3       #
    INT64: int = 4       #
    STRING: int = 5      # not supported
    BOOL: int = 6        # not supported
    INT16: int = 7       #
    COMPLEX64: int = 8   # not supported
    INT8: int = 9        #
    FLOAT64: int = 10    #
    COMPLEX128: int = 11 # not supported
    UINT64: int = 12     #
    UINT32: int = 15     #
    UINT16: int = 16     #

    TF_TO_ST_TYPE: dict[int, str] = {
        INT8: "I8",
        UINT8: "U8",
        INT16: "I16",
        UINT16: "U16",
        INT32: "I32",
        UINT32: "U32",
        INT64: "I64",
        UINT64: "U64",
        FLOAT32: "F32",
        FLOAT64: "F64",
    }


    def __init__(self, entry: Any, buffer: Any) -> None:
        self._entry = entry
        self._buffer = buffer


    def get_type(self) -> str:
        # Type defaults to FLOAT32 when not defined.
        _type = 0
        if 'type' in self._entry:
            _type = struct.unpack('B', self._entry['type'])[0]
        return Tensor.TF_TO_ST_TYPE[_type]


    def get_shape(self) -> list[Any]:
        return list(self._entry['shape'].value)


    def get_data_bytes(self) -> Any:
        if 'data' not in self._buffer:
            return b''
        return self._buffer['data'].value


    def as_array(self) -> None:
        raise NotImplementedError()


    def as_numpy(self) -> Any:
        # In tflite, if DataLength() is 0, DataAsNumpy returns 0.
        data = self.get_data_bytes()
        if len(data) == 0:
            return 0
        res = numpy.frombuffer(data, dtype=Tensor.STTYPE_NP_MAP[self.get_type()])
        res.reshape(self.get_shape())
        return res


class TFLite:


    def __init__(self) -> None:
        self._extraction: Optional[pparse.BytesExtraction] = None
        self._tensors: dict[str, Tensor] = {}


    def _parse(self, data_source: Any, fname: str = "unnamed.tflite", recursion: Optional[pparse.RecursionControl] = None) -> TFLite:

        import json
        from importlib import resources
        from pathlib import Path

        data_path = resources.files("thirdparty.pparse.data")
        with open(data_path/"fbs"/"tflite"/"schema.json", "r") as fobj:
            json_schema = json.loads(fobj.read())

        try:
            data_range = pparse.Range(data_source.open(), data_source.length)
            self._extraction = pparse.BytesExtraction(name=fname, reader=data_range)
            parser_class = configure_pparser(ext_list=[Path(fname).suffix], json_schema=json_schema)
            parser = parser_class(self._extraction, 'flatbuffers')

            self._extraction.add_result('flatbuffers', parser.make_root_node())
            self._extraction._result['flatbuffers'].load(recursion=recursion)

            #self._extraction.add_parser('flatbuffers', parser)
            #self._extraction.discover_parsers({"flatbuffers": parser})
            #self._extraction._parser['flatbuffers']._root.load(recursion=recursion)

            root_table = self.root_node().value['root_table'].value
            buffers = root_table['buffers'].value
            for _entry in root_table['subgraphs'].value[0].value['tensors'].value:
                entry = _entry.value
                buffer = buffers[entry['buffer']].value
                self._tensors[entry['name']] = Tensor(entry, buffer)


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


    # TEST: curl http://host.containers.internal:44444/yolov5su_float32.tflite
    def open_url(self, url: str, recursion: Optional[pparse.RecursionControl] = None) -> TFLite:
        return self._parse(pparse.HttpCachedData(url=url), fname=url, recursion=recursion)


    def open_fpath(self, fpath: str, recursion: Optional[pparse.RecursionControl] = None) -> TFLite:
        return self._parse(pparse.FileData(path=fpath), fname=fpath, recursion=recursion)


    def from_bytesio(self, bytes_io: Any, fname: str = "unnamed.tflite", recursion: Optional[pparse.RecursionControl] = None) -> TFLite:
        return self._parse(pparse.BytesIoData(bytes_io=bytes_io), fname=fname, recursion=recursion)


    def tensor_names(self) -> list[str]:
        return list(self._tensors.keys())


    def tensor(self, name: str) -> Tensor:
        return self._tensors[name]

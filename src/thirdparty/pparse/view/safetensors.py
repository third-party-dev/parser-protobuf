#!/usr/bin/env python3

import os
import struct
import numpy

from thirdparty.pparse.lib import Data, Extraction, EndOfDataException
from thirdparty.pparse.lazy.json import Parser as LazyJsonParser
from thirdparty.pparse.lazy.safetensors import Parser as LazySafetensorsParser

import thirdparty.pparse.lib as pparse


class Tensor():

    STTYPE_STRUCT = {
        'i8': 'b',
        'u8': 'B',
        'i16': 'h',
        'u16': 'H',
        'i32': 'i',
        'u32': 'I',
        'i64': 'q',
        'u64': 'Q',
        'f32': 'f',
        'f64': 'd',
    }

    STTYPE_SIZE = {
        'i8': 1,
        'u8': 1,
        'i16': 2,
        'u16': 2,
        'i32': 4,
        'u32': 4,
        'i64': 8,
        'u64': 8,
        'f32': 4,
        'f64': 8,
    }


    def __init__(self, safetensors, node_map):
        self._safetensors = safetensors
        self._reader = self._safetensors._extraction.open()
        self._node_map = node_map


    def get_type(self):
        return self._node_map.value['dtype'].lower()


    def get_shape(self):
        return self._node_map.value['shape'].value


    def get_offsets(self):
        return self._node_map.value['data_offsets'].value


    def get_data_bytes(self):
        # TODO: Sanity check input.
        header_length = self._safetensors.header_length()
        offsets = self.get_offsets()
        length = offsets[1] - offsets[0]
        self._reader.seek(offsets[0]+header_length+8)
        # TODO: Do we have type aligned length of data?
        self._data = self._reader.read(length)

        if len(self._data) < length:
            raise Exception(f"Missing tensor data: {len(data)}/{length} @ {offset[0]}")


    def as_array(self):
        # TODO: Sanity check input.
        self.get_data_bytes()
        dtype = self.get_type()
        struct_type = Tensor.STTYPE_STRUCT[dtype]
        sttype_size = Tensor.STTYPE_SIZE[dtype]
        count = int(len(self._data) / sttype_size)
        return struct.unpack(f"<{struct_type*count}", self._data)


    def as_numpy(self):
        self.get_data_bytes()
        dtype = self.get_type()
        struct_type = Tensor.STTYPE_STRUCT[dtype]
        shape = self.get_shape()
        return numpy.frombuffer(self._data, dtype=numpy.dtype(f'<{struct_type}')).reshape(shape)


class SafeTensors():
    PARSER_REGISTRY = {
        'json': LazyJsonParser,
        'safetensors': LazySafetensorsParser,
    }


    def __init__(self):
        self._extraction = None


    def header_length(self):
        if not self._extraction:
            raise Exception("No parsed extraction found.")

        return self._extraction._result['safetensors'].header_length


    def header(self):
        if not self._extraction:
            raise Exception("No parsed extraction found.")

        st_init = self._extraction._result['safetensors']
        hdr_init = st_init.parser.source()._extractions[0]._result['json']
        hdr_map = hdr_init.value.value

        return hdr_map


    def metadata(self):
        if not self._extraction:
            raise Exception("No parsed extraction found.")

        hdr_map = self.header()
        return hdr_map['__metadata__']


    def tensor(self, name):
        if not self._extraction:
            raise Exception("No parsed extraction found.")

        hdr_map = self.header()
        if name not in hdr_map:
            raise ValueError(f"No tensor found with name: {name}")
        return Tensor(self, hdr_map[name])


    def open_fpath(self, fpath):
        try:
            cursor = Data(path=fpath).open()
            length = os.path.getsize(fpath)
            rrange = pparse.Range(cursor, length)
            self._extraction = Extraction(reader=rrange, name=fpath)
            self._extraction.discover_parsers(SafeTensors.PARSER_REGISTRY)
            self._extraction.scan_data()
        except EndOfDataException:
            pass
        except Exception as e:
            print(e)
            import traceback
            traceback.print_exc()

        return self


# TODO: Implement this.
class SafeTensorsIndex():
    def __init__(self):
        raise NotImplemented("SafeTensorsIndex not implemented yet.")

#!/usr/bin/env python3

import os
import struct
import numpy
import logging
log = logging.getLogger(__name__)

from pprint import pprint
import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.zip import Parser as LazyZipParser


class PyTorch():
    


    def __init__(self, extraction=None):
        self._extraction = extraction


    def open_fpath(self, fpath):
        try:
            # --- Scan the zip ---
            ZIP_PARSER_REGISTRY = { 'zip': LazyZipParser, }
            data_source = pparse.Data(path=fpath)
            data_range = pparse.Range(data_source.open(), data_source.length)
            self._zip_extraction = pparse.BytesExtraction(name=fpath, reader=data_range)
            self._zip_extraction.discover_parsers(PyTorch.PARSER_REGISTRY)
            self._zip_extraction.scan_data()

            # TODO: Zip Parser should skip data, so we want to query data.pkl data here.

            # --- Scan the data.pkl member ---
            self.data_pkl_meta = self._zip_extraction._result['zip'].value[0].value
            # TODO: Verify value[0] _is_ "data.pkl"
            data_pkl_buf = self.data_pkl_meta['decomp_data'].value.getbuffer()
            # ! TODO: Make pparse.Data accept ByteIO or buffer?
            # self.data_pkl_range = pparse.Range(data_pkl_buf, len(data_pkl_buf))
            # data_source = pparse.Data(path='output/gpt2-pytorch/data.pkl')
            # data_range = pparse.Range(data_source.open(), data_source.length)

            PKL_PARSER_REGISTRY = { 'pkl': LazyPickleParser, }
            self._pkl_extraction = pparse.BytesExtraction(name='data.pkl', reader=self.data_pkl_range)
            self._pkl_extraction.discover_parsers(PKL_PARSER_REGISTRY).scan_data()



















'''
PERSID_CALL(
    arg=(b'storage',     storage-type persistent ID
         (b'torch\n', b'FloatStorage\n'),   module/typename
         b'147',    storage key
         b'cpu',    device
         768)       data size in bytes
)

newer format uses `data/{key}`
older format used `tensors/{key}`

bytesize = 768
dtype = float32
float elements = 768/4 = 192

floats = struct.unpack('192f', raw)

OR

arr = np.frombuffer(raw, dtype=np.float32)

def load_storage(data_zip, storage_id, dtype, byte_size):
    raw = data_zip.read(f"data/{storage_id.decode()}")
    return np.frombuffer(raw[:byte_size], dtype=dtype)

'''


'''

REDUCE_CALL(
  mod=b'torch._utils\n',
  func=b'_rebuild_tensor_v2\n',
  arg=(
      PERSID_CALL(
        arg=(
            b'storage',
            (b'torch\n', b'FloatStorage\n'),
            b'147',
            b'cpu',
            768
        )
      ),
      0,
      (768,),
      (1,),
      False,
      REDUCE_CALL(
        mod=b'collections\n',
        func=b'OrderedDict\n',
        arg=()
      )
  )
)



import numpy as np

# from the storage record:
raw = ...  # load raw bytes from archive
storage_arr = np.frombuffer(raw, dtype=np.float32)

# from the tensor record:
offset = 0
size = (768,)
stride = (1,)

tensor_arr = np.lib.stride_tricks.as_strided(
    storage_arr[offset:], 
    shape=size, 
    strides=(stride[0] * 4,)  # float32 bytes
)

print(tensor_arr)



'''


'''

Plan:

For a number of pytorch versions:
  - Iterate over an array of transformer types and output as pytorch.
  - Grab the pytorch data pickle for the transformer defaults and save off.

Does CUDA generate a different output?
What hardware do I need to check CUDA output?

'''
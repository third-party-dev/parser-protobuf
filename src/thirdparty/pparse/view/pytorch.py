#!/usr/bin/env python3

import os
import struct
import numpy
import logging
log = logging.getLogger(__name__)

from pprint import pprint
import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.zip import Parser as LazyZipParser
from thirdparty.pparse.lazy.pickle import Parser as LazyPickleParser

# For debug

#from pprintpp import pprint

'''
    # F32  | FloatStorage         | torch.float32    | np.float32
    # F64  | DoubleStorage        | torch.float64    | np.float64
    # F16  | HalfStorage          | torch.float16    | np.float16
    # BF16 | BFloat16Storage      | torch.bfloat16   | np.dtype("bfloat16")
    # I8   | CharStorage          | torch.int8       | np.int18
    # I16  | ShortStorage         | torch.int16      | np.int16
    # I32  | IntStorage           | torch.int32      | np.int32
    # I64  | LongStorage          | torch.int64      | np.int64
    # U8   | ByteStorage          | torch.uint8      | np.uint8
    # BOOL | BoolStorage          | torch.bool       | np.bool_
    # N/A  | ComplexFloatStorage  | torch.complex64  | np.complex64
    # N/A  | ComplexDoubleStorage | torch.complex128 | np.complex128
    # I8?  | QInt8Storage         | torch.qint8      | np.int8
    # U8?  | QUInt8Storage        | torch.quint8     | np.uint8
    # U32? | QInt32Storage        | torch.qint32     | np.int32
'''

class Tensor(pparse.Tensor):

    PKL_STTYPE_MAP = {
        'torch.FloatStorage': 'F32',
        'torch.DoubleStorage': 'F64',
        'torch.HalfStorage': 'F16',
        'torch.BFloat16Storage': 'BF16',
        'torch.CharStorage': 'I8',
        'torch.ShortStorage': 'I16',
        'torch.IntStorage': 'I32',
        'torch.LongStorage': 'I64',
        'torch.ByteStorage': 'U8',
        'torch.BoolStorage': 'BOOL',
        
        # # Unknown safetensor equivalency.
        # 'ComplexFloatStorage': '',
        # 'ComplexDoubleStorage': '',
        # # Map guessed based on np equivalency
        # 'QInt8Storage': 'I8',
        # 'QUInt8Storage': 'U8',
        # 'QInt32Storage': 'I32',
    }

    PERSID_CALL = 0

    TYPE_TAG = 0
    TYPE_NAME = 1
    DATA_KEY = 2
    DATA_DEST = 3
    ELEM_CNT = 4


    def __init__(self, pytorch_view, reduce_call_node, name):
        self._name = name
        self._view = pytorch_view
        self._reduce_call = reduce_call_node


    # Return (safetensors equivalent) type
    def get_type(self) -> str:
        # Note: Assuming tuple
        return Tensor.PKL_STTYPE_MAP[self.get_pytorch_type()]
        # TEST: obj.tensor('lm_head.weight').get_type()


    def get_pytorch_type(self) -> str:
        persid = self._reduce_call.arg[Tensor.PERSID_CALL]
        parts = [p.decode('utf-8').strip() for p in persid.arg[Tensor.TYPE_NAME]]
        return '.'.join(parts)
        # TEST: obj.tensor('lm_head.weight').get_pytorch_type()

        # type_tag = persid.arg[Tensor.TYPE_TAG]
        # type_name = persid.arg[Tensor.TYPE_NAME]
        # # torch.FloatStorage => dtype=float32
        # data_key = persid.arg[Tensor.DATA_KEY]
        # data_dest = persid.arg[Tensor.DATA_DEST]
        # elem_cnt = persid.arg[Tensor.ELEM_CNT]


    # Return (safetensors equivalent) shape
    def get_shape(self):
        raise NotImplementedError()


    # Return raw data as extracted from source
    def get_data_bytes(self):
        from pathlib import Path

        persid = self._reduce_call.arg[Tensor.PERSID_CALL]
        type_tag = persid.arg[Tensor.TYPE_TAG]
        if type_tag != 'storage':
            raise Exception("Unexpected TYPE_TAG format when fetching tensor bytes.")
        data_key = persid.arg[Tensor.DATA_KEY]
        elem_cnt = persid.arg[Tensor.ELEM_CNT]

        for member in self._view._extraction._result['zip'].value:
            fname_parts = Path(member.value['fname']).parts
            if len(fname_parts) < 2 or fname_parts[-2] != 'data':
                continue
            if fname_parts[-1] == data_key:
                # TODO: Consider the value could be unloaded.
                bytes_io = member.value['decomp_data'].value
                return bytes_io.getbuffer()

        raise Exception(f"Data not found for tensor: {self._name}")
        # TEST: obj.tensor('lm_head.weight').get_data_bytes()


    # Return raw data as python array of dtype
    def as_array(self):
        # TODO: Sanity check input.
        persid = self._reduce_call.arg[Tensor.PERSID_CALL]
        elem_cnt = persid.arg[Tensor.ELEM_CNT]
        buffer = self.get_data_bytes()
        dtype = self.get_type()
        struct_type = pparse.Tensor.STTYPE_STRUCT[dtype]
        sttype_size = pparse.Tensor.STTYPE_SIZE[dtype]
        count = int(len(buffer) / sttype_size)
        return struct.unpack(f"<{struct_type*count}", buffer)
        # TEST: obj.tensor('lm_head.weight').as_array()


    # Return raw data as numpy array of dtype
    def as_numpy(self):
        persid = self._reduce_call.arg[Tensor.PERSID_CALL]
        elem_cnt = persid.arg[Tensor.ELEM_CNT]
        buffer = self.get_data_bytes()
        np_type = pparse.Tensor.STTYPE_NP_MAP[self.get_type()]
        print(f"len {len(buffer)} np_type {np_type} elem_cnt {elem_cnt}")
        return numpy.frombuffer(buffer, dtype=np_type, count=elem_cnt)
        # TEST: obj.tensor('lm_head.weight').as_numpy()


class PyTorch():
    
    def __init__(self, extraction=None):
        self._extraction = extraction


    def open_fpath(self, fpath):
        
        # --- Scan the zip ---
        ZIP_PARSER_REGISTRY = { 'zip': LazyZipParser, }
        data_source = pparse.FileData(path=fpath)
        data_range = pparse.Range(data_source.open(), data_source.length)
        self._extraction = pparse.BytesExtraction(name=fpath, reader=data_range)
        self._extraction.discover_parsers(ZIP_PARSER_REGISTRY)
        self._extraction.scan_data()

        # TODO: Zip Parser should skip data, so we want to query data.pkl data here.

        # --- Scan the data.pkl member ---
        print("Parsing pkl of fpath")
        # Assumption: First file is always data.pkl. (We _could_ search.)
        self.data_pkl_meta = self._extraction._result['zip'].value[0].value
        if os.path.basename(self.data_pkl_meta['fname']) != 'data.pkl':
            raise Exception("data.pkl was not first file in zip as expected.")
        
        # Assumption: decomp_data will have the data. Consider checking for unloaded_data.
        self.pkl_source = pparse.BytesIoData(self.data_pkl_meta['decomp_data'].value)
        self.pkl_range = pparse.Range(self.pkl_source.open(), self.pkl_source.length)
        PKL_PARSER_REGISTRY = { 'pkl': LazyPickleParser, }

        self._pkl_extraction = pparse.BytesExtraction(name='data.pkl', reader=self.pkl_range)
        self._extraction._extractions.append(self._pkl_extraction)
        self._pkl_extraction.discover_parsers(PKL_PARSER_REGISTRY).scan_data()

        return self


    def tensor(self, name):
        pkl = self._pkl_extraction._result['pkl']
        tensor_dict = pkl.value[0].value[0]
        if name not in tensor_dict:
            raise KeyError("Tensor name not found.")

        return Tensor(self, tensor_dict[name], name)
        

    def tensor_names(self):
        pkl = self._pkl_extraction._result['pkl']
        tensor_dict = pkl.value[0].value[0]
        return [k for k in tensor_dict]


        '''
            pkl = obj._extraction._extractions[0]._result['pkl']
            tensor_dict = pkl.value[0].value[0]
            tensor_list = tensor_dict.keys()
            history = pkl.value[0].history
            print(pparse_repr(tensor_dict['transformer.ln_f.bias']))

            reduce_call = tensor_dict['transformer.ln_f.bias']
            persid_call = reduce_call.arg[0]
            type_tag = persid_call.arg[0]
            type_name = persid_call.arg[1]
            # torch.FloatStorage => dtype=float32
            data_key = persid_call.arg[2]
            data_dest = persid_call.arg[3]
            elem_cnt = persid_call.arg[4]

            #import numpy as np
            #raw = read_bytes_for_id("147")
            #arr = np.frombuffer(raw, dtype=np.float32, count=768)

            # FloatStorage         | torch.float32    | np.float32
            # DoubleStorage        | torch.float64    | np.float64
            # HalfStorage          | torch.float16    | np.float16
            # BFloat16Storage      | torch.bfloat16   | np.dtype("bfloat16")
            # CharStorage          | torch.int8       | np.int18
            # ShortStorage         | torch.int16      | np.int16
            # IntStorage           | torch.int32      | np.int32
            # LongStorage          | torch.int64      | np.int64
            # ByteStorage          | torch.uint8      | np.uint8
            # BoolStorage          | torch.bool       | np.bool_
            # ComplexFloatStorage  | torch.complex64  | np.complex64
            # ComplexDoubleStorage | torch.complex128 | np.complex128
            # QInt8Storage         | torch.qint8      | np.int8
            # QUInt8Storage        | torch.quint8     | np.uint8
            # QInt32Storage        | torch.qint32     | np.int32

            # No UInt16Storage, UInt32Storage, UInt64Storage
        '''


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
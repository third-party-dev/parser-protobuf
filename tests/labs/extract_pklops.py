#!/usr/bin/env python3

from pprintpp import pprint
import thirdparty.pparse.lib as pparse 
from thirdparty.pparse.lazy.pickle import Parser as LazyPickleParser
from thirdparty.pparse.utils import pparse_repr

try:

    parser_reg = {'pkl': LazyPickleParser}
    data_source = pparse.Data(path='output/gpt2-weights/data.pkl')
    data_range = pparse.Range(data_source.open(), data_source.length)
    root = pparse.BytesExtraction(name='output/gpt2-weights/data.pkl', reader=data_range)
    root.discover_parsers(parser_reg).scan_data()

except pparse.EndOfDataException as e:
    print(e)
    pass
except Exception as e:
    print(e)
    import traceback
    traceback.print_exc()

#pprint(root._result['pkl'].value[0].value)
#pprint(root._result['pkl'].value[0].ctx().history)
pkl = root._result['pkl']
obj = pkl.value[0].value[0]
history = root._result['pkl'].value[0].history
with open('dump.yaml', 'w') as repr_fobj:
    repr_fobj.write(pparse_repr(obj))
    #print(pparse_repr(obj))
breakpoint()




import numpy

class TensorProcessor():
    def __init__(self, obj, tensor_name):
        self.tensor_name = tensor_name
        self.pickle_obj = obj[self.tensor_name]
        self.modcall = self.pickle_obj.module_call

        # Load the metadata.
        if self.modcall == (b'torch._utils\n', b'_rebuild_tensor_v2\n'):
            print(f"Processing target {self.modcall}.")
            arg = self.pickle_obj.arg

            from thirdparty.pparse.lazy.pickle.state import PersistentCall
            
            if isinstance(arg[0], PersistentCall):
                print("Found persistent call (to load raw data).")
                persid_arg = arg[0].arg
                self.storage_type = persid_arg[0]
                self.mod_type_name = persid_arg[1]

                if self.mod_type_name == (b'torch\n', b'FloatStorage\n'):
                    self.d_type = numpy.float32
                else:
                    print(f'Unknown numpy data type. mod_type_name: {self.mod_type_name}')
                    breakpoint()

                self.storage_key = persid_arg[2].decode('utf-8') # data file
                self.device = persid_arg[3] # unused by pparse
                self.data_size = persid_arg[4] # data byte size

            else:
                print(f"Unknown persistence call type: {type(arg[0])}")
                breakpoint()

            self.d_offset = arg[1]
            self.d_shape = arg[2]
            self.d_stride = arg[3]
        
        else:
            print(f"Unknown reduce call type: {type(arg[0])}")
            breakpoint()


    # Load the tensor data.
    def load(self):
        with open(f'output/gpt2-weights/data/{self.storage_key}', "rb") as tensor_fobj:
            self.tensor_data = tensor_fobj.read()
            self.tensor_arr = numpy.frombuffer(self.tensor_data, dtype=self.d_type)
            # TODO: This is not very space efficient. Consider memoryview.
            # ! TODO: This is not flexible.
            self.tensor_data = numpy.lib.stride_tricks.as_strided(
                self.tensor_arr[self.d_offset:],
                shape=self.d_shape,
                strides=self.d_stride
            )

        return self
            
tensor = TensorProcessor(obj, b'model.encoder.conv1.weight').load()

#print("DUMPING")
#rnode = root._result['protobuf']
#with open("output.txt", "w") as f:
#    f.write(rnode.dumps())

print("ALL DONE")
breakpoint()



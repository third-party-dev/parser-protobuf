#!/usr/bin/env python3

from pprintpp import pprint
import thirdparty.pparse.lib as pparse 
from thirdparty.pparse.lazy.pickle import Parser as LazyPickleParser
from thirdparty.pparse.utils import pparse_repr

try:

    parser_reg = {'pkl': LazyPickleParser}
    data_source = pparse.Data(path='output/gpt2-pytorch/data.pkl')
    data_range = pparse.Range(data_source.open(), data_source.length)
    root = pparse.BytesExtraction(name='output/gpt2-pytorch/data.pkl', reader=data_range)
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
state_dict = obj['model_state_dict']
model_arch = obj['model_architecture']
history = root._result['pkl'].value[0].history

tensor_list = obj['model_state_dict'].keys()

print(pparse_repr(state_dict['transformer.ln_f.bias']))

with open('dump_model_state_dict.yaml', 'w') as repr_fobj:
    repr_fobj.write(pparse_repr(state_dict))

with open('dump_model_architecture.yaml', 'w') as repr_fobj:
    repr_fobj.write(pparse_repr(model_arch))

#breakpoint()




import numpy

class StateDictTensorProcessor():
    def __init__(self, state_dict, tensor_name):
        self.tensor_name = tensor_name
        self.pickle_obj = state_dict[self.tensor_name]
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

                '''
                   Can the persid_arg be in bytes and require .decode('utf-8')?
                   Can the persid_arg be omitted an require a index lookup?
                     `idx = list(state_dict.keys()).index(self.tensor_name)`
                '''
                
                self.storage_key = persid_arg[2]  # data file name
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
        with open(f'output/gpt2-pytorch/data/{self.storage_key}', "rb") as tensor_fobj:
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


'''
Starting in 2.6, torch.load defaults to weights_only=True, which prevents arbitrary code 
execution by only allowing plain tensors and basic containers to be unpickled.
'''

tensor = StateDictTensorProcessor(state_dict, 'transformer.ln_f.bias').load()

print("Loading tranditional pytorch checkpoint")
import torch
checkpoint = torch.load("output/gpt2-pytorch/gpt2-weights.pth.zip", weights_only=False)
# model.load_state_dict(checkpoint['model_state_dict'])
print(checkpoint['model_state_dict']['transformer.ln_f.bias'].numpy()[-16:])

print('--- Safetensors ---')
from thirdparty.pparse.view import SafeTensors
safeobj = SafeTensors().open_fpath('output/gpt2-safetensors/model.safetensors')
safetensor = safeobj.tensor('transformer.ln_f.bias')
safenparr = safetensor.as_numpy()
print(safenparr[-16:])

print('--- PyTorch ---')
print(tensor.tensor_arr[-16:])

#print("DUMPING")
#rnode = root._result['protobuf']
#with open("output.txt", "w") as f:
#    f.write(rnode.dumps())

print("ALL DONE")
breakpoint()


'''

'''
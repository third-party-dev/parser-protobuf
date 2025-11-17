#!/usr/bin/env python3

from thirdparty.pparse.view import Onnx

obj = Onnx().open_fpath('models/decoder_model.onnx')

'''
    # NOTE: If you are going to load everything into memory at once
    # use the following instead:

    import onnx
    from onnx import numpy_helper
    model = onnx.load("model.onnx")
    numpy_weights = {}
    for initializer in model.graph.initializer:
        name = initializer.name
        array = numpy_helper.to_array(initializer)
        numpy_weights[name] = array
        print(name, array.shape, array.dtype)
'''

parser = obj._extraction._parser['protobuf']
model = obj._extraction._result['protobuf'].value
graph = model['graph']
nodes = graph.value['node'].value
node0 = nodes[0].value
input_ids = node0['input'].value
output_ids = node0['output'].value
name = node0['name']

print('')

print(f'Nodes Found: {len(nodes)}')

ops = {}
for node in parser.nodes.values():
    if 'op_type' in node.value:
        ops[node.value['op_type']] = True
print("Operations Found:")
for op in ops:
    print(f'- {op}')

breakpoint()

#for key in obj._extraction._parser['protobuf'].tensors.keys():
#    breakpoint()

'''
    
    
'''



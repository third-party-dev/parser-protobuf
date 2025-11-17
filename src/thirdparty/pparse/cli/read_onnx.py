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

breakpoint()

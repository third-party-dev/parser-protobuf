#!/usr/bin/env python3

from thirdparty.pparse.view import SafeTensors

obj = SafeTensors().open_fpath('model.safetensors')
tensor = obj.tensor('h.3.ln_2.bias')
nparr = tensor.as_numpy()

'''
# NOTE: If you are going to load everything into memory at once
# use the following instead:

from safetensors.numpy import load_file
tensors = load_file("model.safetensors")
nparr = tensors['h.3.ln_2.bias']
'''

breakpoint()

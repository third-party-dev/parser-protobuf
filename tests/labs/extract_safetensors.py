#!/usr/bin/env python3

from pprint import pprint
import thirdparty.pparse.lib as pparse

#from thirdparty.pparse.lib import Data, Extraction, EndOfDataException
from thirdparty.pparse.lazy.json import Parser as LazyJsonParser
from thirdparty.pparse.lazy.safetensors import Parser as LazySafetensorsParser


try:
    parser_reg = {
        'json': LazyJsonParser,
        'safetensors': LazySafetensorsParser,
    }
    # TODO: We should be able to pass a safetensors index as well!
    cursor = pparse.Data(path='output/gpt2-safetensors/model.safetensors').open()
    root = pparse.BytesExtraction(name='model.safetensors', reader=cursor)
    root = root.discover_parsers(parser_reg).scan_data()
except pparse.EndOfDataException:
    pass
except Exception as e:
    print(e)
    import traceback
    traceback.print_exc()

# # Dump output for examination.
# print("Dumping root to output.txt")
# with open("output.txt", "w") as fobj:
#     pprint(root, stream=fobj, indent=2)
# print("Dump complete.")

# json_obj = root._result['json']
# # Dump with unloaded things.
# print(json_obj.dumps())
# # Load defered/truncated value.
# json_obj.value.value['description'].load(json_obj.parser)
# # Dump with loaded things.
# print(root._result['json'].dumps())

tensor_db = root._result['safetensors'].parser.source()._extractions[0]._result['json'].value.value
for k,v in tensor_db.items():
    print(f"{k}: {v}")
breakpoint()

# TODO: Consider converting each (non-"__metadata__") NodeMap into a NodeTensor. Each Tensor can
# then be "load()"ed on demand.

print("ALL DONE")
breakpoint()

'''

'''

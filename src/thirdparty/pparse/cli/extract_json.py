#!/usr/bin/env python3

from pprint import pprint
from thirdparty.pparse.lib import Data, Extraction, EndOfDataException
from thirdparty.pparse.lazy.json import Parser as LazyJsonParser
from thirdparty.pparse.lazy.json.node import Node as LazyJsonNode

try:
    parser_reg = {'json': LazyJsonParser}
    cursor = Data(path='test.json').open()
    root = Extraction(reader=cursor, name='test.json')
    root = root.discover_parsers(parser_reg).scan_data()
except EndOfDataException:
    pass
except Exception as e:
    print(e)
    import traceback
    traceback.print_exc()

# Dump output for examination.
print("Dumping root to output.txt")
with open("output.txt", "w") as fobj:
    pprint(root, stream=fobj, indent=2)
print("Dump complete.")

json_obj = root._result['json']
# Dump with unloaded things.
print(json_obj.dumps())
# Load defered/truncated value.
json_obj.value.value['description'].load(json_obj.parser)
# Dump with loaded things.
print(root._result['json'].dumps())

print("ALL DONE")
breakpoint()



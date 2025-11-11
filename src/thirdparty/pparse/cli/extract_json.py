#!/usr/bin/env python3

from pprint import pprint
from thirdparty.pparse.lib import Data, Extraction, EndOfDataException
from thirdparty.pparse.parser.lazyjson import LazyJsonParser

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

#print(artifact.candidates['json']['meta']['root'].child.map)

breakpoint()

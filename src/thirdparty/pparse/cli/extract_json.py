#!/usr/bin/env python3

from pprint import pprint
from thirdparty.pparse.lib import pparse, Data, Extraction, PARSERS, EndOfDataException
from thirdparty.pparse.parser.lazyjson import LazyJsonParser

PARSERS['json'] = LazyJsonParser

try:
    cursor = Data(path='test.json').open()
    root = Extraction(reader=cursor).discover_parsers(PARSERS).scan_data()
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

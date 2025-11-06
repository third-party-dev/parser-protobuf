#!/usr/bin/env python3

from pprint import pprint
from thirdparty.pparse.lib import Data, Artifact, PARSERS
from thirdparty.pparse.parser.json import JsonParser

PARSERS['json'] = JsonParser

# Data is independent of Artifact/Parser tree.
data = Data(path='test.json')

try:
    # Top Artifact has not parent parser.
    cursor = data.open()
    artifact = Artifact(cursor)
    artifact.set_fname('test.json')
    artifact.scan_data()
except Exception as e:
    print(e)
    import traceback
    traceback.print_exc()


# Dump output for examination.
print("Dumping root to output.txt")
with open("output.txt", "w") as fobj:
    pprint(artifact, stream=fobj, indent=2)
print("Dump complete.")

#breakpoint()
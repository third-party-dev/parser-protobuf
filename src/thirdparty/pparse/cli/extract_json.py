#!/usr/bin/env python3

from pprint import pprint
from thirdparty.pparse.lib import Data, Extraction, EndOfDataException
from thirdparty.pparse.parser.lazyjson import LazyJsonParser, LazyJsonNode

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

def dumpall(node, depth=0):
    #breakpoint()
    if isinstance(node.value, LazyJsonNode):
        dumpall(node.value, depth+2)
    if isinstance(node.value, dict):
        print(f" {' ' * (depth-2)}" "{")
        for k,v in node.value.items():
            if isinstance(v, LazyJsonNode):
                print(f"{' ' * depth} {k}: ")
                dumpall(v, depth+2)
            else:
                print(f"{' ' * depth} {k}: {v}")
        print(f" {' ' * (depth-2)}" "}")
    elif isinstance(node.value, list):
        print(f" {' ' * (depth-2)}" "[")
        for e in node.value:
            if isinstance(e, LazyJsonNode):
                dumpall(e, depth+2)
            else:
                print(f"{' ' * depth} {e},")
        print(f" {' ' * (depth-2)}" "]")
    else:
        print(f"{' ' * depth} {node.value}")


dumpall(root._result['json'])

root._result['json'].value.value['description'].load(root._parser['json'])

dumpall(root._result['json'])

print("ALL DONE")
breakpoint()



'''
root._result['json'].value.value['tags'].value

root._result['json'].value.value['description']

root._result['json'].value.value['description'].load(root._parser['json'])

root._result['json'].value.value['description'].value
'''
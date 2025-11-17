#!/usr/bin/env python3

from pprint import pprint
from thirdparty.pparse.lib import Data, Extraction, EndOfDataException, Range
from thirdparty.pparse.lazy.protobuf import Parser as LazyProtobufParser

try:
    parser_reg = {'protobuf': LazyProtobufParser}
    data_source = Data(path='models/decoder_model.onnx')
    data_range = Range(data_source.open(), data_source.length)
    root = Extraction(reader=data_range, name='models/decoder_model.onnx')
    root = root.discover_parsers(parser_reg).scan_data()
except EndOfDataException as e:
    print(e)
    pass
except Exception as e:
    print(e)
    import traceback
    traceback.print_exc()

print("DUMPING")

rnode = root._result['protobuf']
with open("output.txt", "w") as f:
    f.write(rnode.dumps())

print("ALL DONE")
breakpoint()



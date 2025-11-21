#!/usr/bin/env python3

from pprint import pprint
import thirdparty.pparse.lib as pparse 
from thirdparty.pparse.lib import Data, Extraction, EndOfDataException
from thirdparty.pparse.lazy.zip import Parser as LazyZipParser

try:

    parser_reg = {'zip': LazyZipParser}
    data_source = pparse.Data(path='models/pytorch_model.zip')
    data_range = pparse.Range(data_source.open(), data_source.length)
    root = pparse.Extraction(reader=data_range, name='models/pytorch_model.zip')
    root.discover_parsers(parser_reg).scan_data()

except pparse.EndOfDataException as e:
    print(e)
    pass
except Exception as e:
    print(e)
    import traceback
    traceback.print_exc()

#print("DUMPING")
#rnode = root._result['protobuf']
#with open("output.txt", "w") as f:
#    f.write(rnode.dumps())

print("ALL DONE")
breakpoint()



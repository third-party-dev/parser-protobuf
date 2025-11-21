#!/usr/bin/env python3

from pprint import pprint
import thirdparty.pparse.lib as pparse 
from thirdparty.pparse.lazy.pickle import Parser as LazyPickleParser

try:

    parser_reg = {'pkl': LazyPickleParser}
    data_source = pparse.Data(path='models/data.pkl')
    data_range = pparse.Range(data_source.open(), data_source.length)
    root = pparse.Extraction(reader=data_range, name='models/data.pkl')
    root.discover_parsers(parser_reg).scan_data()

except pparse.EndOfDataException as e:
    print(e)
    pass
except Exception as e:
    print(e)
    import traceback
    traceback.print_exc()

# pprint(root._result['pkl'].value[0].value[0])

#l9key = 'model.encoder.layers.9.self_attn_layer_norm.weight'
#l9 = root._result['pkl'].value[0].value[0][l9key]

obj = root._result['pkl'].value[0].value[0]
# pprint(obj[b'model.encoder.layers.9.self_attn_layer_norm.weight'])

#print("DUMPING")
#rnode = root._result['protobuf']
#with open("output.txt", "w") as f:
#    f.write(rnode.dumps())

print("ALL DONE")
breakpoint()



#!/usr/bin/env python3

from pprint import pprint
import thirdparty.pparse.lib as pparse

from thirdparty.pparse.lazy.zip import Parser as LazyZipParser

import os
import logging
log = logging.getLogger(__name__)

level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, level, logging.INFO))

try:
    log.debug("Debug log level enabled.")
    parser_reg = { 'zip': LazyZipParser, }
    data_source = pparse.Data(path='output/gpt2-pytorch/gpt2-weights.pth.zip')
    data_range = pparse.Range(data_source.open(), data_source.length)
    root = pparse.BytesExtraction(name='gpt2-weights.pth.zip', reader=data_range)
    root.discover_parsers(parser_reg).scan_data()

except pparse.EndOfDataException:
    pass
except Exception as e:
    print(e)
    import traceback
    traceback.print_exc()


zip_member_nodes = root._result['zip'].value
data_pkl_meta = root._result['zip'].value[0].value
data_pkl = data_pkl_meta['decomp_data'].value
data_pkl_len = len(data_pkl.getbuffer())

print("ALL DONE")
breakpoint()

'''

'''

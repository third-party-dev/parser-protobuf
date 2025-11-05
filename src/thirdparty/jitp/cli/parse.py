#!/usr/bin/env python3

import os

from pprint import pprint

from thirdparty.jitp.lib.utils import EndOfDataException, hexdump, UnsupportedFormatException

from thirdparty.jitp.decoder.json import JsonParser

PARSERS['json'] = JsonParser

# Considerations:
# - sequential reads faster than mmap, but only due to readahead
# - random access seeking also breaks readahead.
class JitCursor():
    def __init__(self, jitdata, offset=0):
        self.jitdata = jitdata
        self.offset = offset

    # Read data ahead without progressing cursor.
    def peek(self, length):
        self.jitdata.fobj.seek(os.SEEK_SET, offset)
        self.jitdata.fobj.read(length)
    
    # Progress cursor without reading (no copy).
    def seek(self, offset):
        self.offset = offset
        self.jitdata.fobj.seek(os.SEEK_SET, offset)
    
    # Copy and progress data.
    def read(self, length):
        self.offset = offset
        self.jitdata.fobj.seek(os.SEEK_SET, offset)
        self.jitdata.fobj.read(length)

    # Where in the JitData are we
    def tell(self):
        return self.offset
        

class JitData():
    def __init__(self, path=None):
        self.path = path
        self.fobj = open(path, "rb")

    def open(self, offset=0):
        return JitCursor(self, offset)
    




root = JustInTimeParser(path='test.json') # Used to be PObjBuffer()

json_parser = root.get_candidate('json')
json_children = json_parser.children()



    try:
        with open(fpath, 'rb') as f:
            root.add_data(f.read())
            root.meta['fname'] = fpath
            root.process_data()
    except EndOfDataException as e:
        pass
    except UnsupportedFormatException as e:
        print(e)
        pass

    print("Dumping root to output.txt")
    with open("output.txt", "w") as fobj:
        pprint(root, stream=fobj, indent=2)
    print("Dump complete.")
    


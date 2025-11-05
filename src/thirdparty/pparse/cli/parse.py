#!/usr/bin/env python3

from pprint import pprint

from thirdparty.pparse.lib.utils import MultiUseBuffer, EndOfDataException, hexdump, UnsupportedFormatException
from thirdparty.pparse.lib.pobj import PObjBuffer, PObjParser, PARSERS

from thirdparty.pparse.decoder.json import JsonParser

PARSERS['json'] = JsonParser

for fpath in ['models/decoder_model.onnx']:
    root = PObjBuffer()
    print(f"Parsing {fpath}")

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
    


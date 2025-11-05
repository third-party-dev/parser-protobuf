#!/usr/bin/env python3

from thirdparty.pparse.lib.utils import MultiUseBuffer, EndOfDataException
from typing import Optional
import json

PARSERS = {}

class PObjBuffer(dict):
    def __init__(self, parent: Optional['PObjParser'] = None):
        self.parent: Optional['PObjParser'] = parent
        self.buffer: MultiUseBuffer = MultiUseBuffer()

        self.meta = {
            'fname': None,
            'byte_count': 0,
            'offset': -1,
            'candidates': {},
        }

        self.candidates: dict = self.meta['candidates']
        dict.__init__(self, meta=self.meta)

    def add_data(self, data: MultiUseBuffer):
        self.meta['byte_count'] += len(data)
        self.buffer.write(data)

    def length(self):
        return self.buffer.length
    
    def process_data(self):
        global PARSERS
        for (pname, parser) in PARSERS.items():

            if pname not in self.candidates:
                if parser.match_extension(self):
                    self.candidates[pname] = parser(self, pname)
                    continue
                if parser.match_magic(self):
                    self.candidates[pname] = parser(self, pname)
                    continue
            
            for (cname, candidate) in self.candidates.items():
                candidate.process_data()

class PObjParser(dict):

    def __init__(self, parent: PObjBuffer, id: str):
        if not isinstance(parent, PObjBuffer):
            raise TypeError("Parent must be a PObjBuffer")
        self.id: str = id
        self.parent: PObjBuffer = parent

        self.buffer: MultiUseBufferReader = parent.buffer.get_reader()

        self.meta: dict = { 'children': [] }
        self.children: list = self.meta['children']

        dict.__init__(self, meta=self.meta)

    def process_data(self):
        raise NotImplementedError()

    

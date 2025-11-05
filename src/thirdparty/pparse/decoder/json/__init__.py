import sys
import struct
import zlib
import os
import urllib.parse
import io
import tarfile
import json

import argparse
import pdb

from typing import Optional
from thirdparty.pparse.lib.utils import MultiUseBuffer, EndOfDataException, UnsupportedFormatException
from thirdparty.pparse.lib.pobj import PObjParser, PObjBuffer

class JsonParsingState(object):
    def parse_data(self, context: PObjParser):
        raise NotImplementedError()

class JsonParsingNumber(JsonParsingState):
    def parse_data(self, context: PObjParser):
        data = context.buffer.peek(0x400)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON whitespace")
        
        NUM_BYTES = b'\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39' \
                    b'\x2d\x2b\x65\x45\x2e'
        
        offset = 0
        done = False
        while offset < len(data):
            if not data[offset:offset + 1] in NUM_BYTES:
                done = True
                break
            context.num_Bytes.append(data[offset:offset+1])
            offset += 1
        context.buffer.read(offset)

        if done:
            try:
                context._apply_value(json.loads(b''.join(context.num_bytes)))
            except Exception as e:
                raise UnsupportedFormatException(f"Invalid number format in {context.num_bytes}: {e}")
            finally:
                context.num_bytes = []
            
        context._next_state(JsonParserMeta)

class JsonParsingString(JsonParsingState):
    def parse_data(self, context: PObjParser):
        data = context.buffer.peek(0x400)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse JSON string.")
        
        offset = 0
        while offset < len(data) and len(data) - offset > 1:
            if data[offset:offset+1] == b'\x22':
                # We're done
                try:
                    context.str_bytes.append(context.buffer.read(offset+1))
                    context._apply_value(json.loads(b''.join(context.str_bytes)))
                except Exception as e:
                    raise UnsupportedFormatException(f"Invalid string format in {context.str_bytes}: {e}")
                finally:
                    context.str_bytes = ['"']
                
                context._next_state(JsonParserMeta)
                return
        
            elif data[offset:offset+1] == b'\x5c':
                if data[offset+1:offset+2] == b'\x75':
                    if len(data) < 6:
                        raise EndOfDataException("Not enough bytes to parse JSON enicode char in string.")
                    context.str_bytes.append(data[offset:offset+6])
                    offset += 6
                    continue
                if data[offset+1] in b'\x22\x5c\x2f\x62\x66\x6e\x72\x74':
                    context.str_bytes.append(data[offset:offset+2])
                    offset += 2
                    continue

            else:
                offset += 1
        
        context.str_bytes.append(context.buffer.read(offset))

class JsonParsingWhitespace(JsonParsingState):
    def parse_data(self, context: PObjParser):
        data = context.buffer.peek(0x400)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON whitespace.")
        
        offset = 0
        while offset < len(data):
            if not data[offset:offset+1] in b'\x09\x0a\x0d\x20':
                break
            offset += 1
        context.buffer.read(offset)

        context._next_state(JsonParsingMeta)

class JsonParsingConstant(JsonParsingState):
    def parse_data(self, context: PObjParser):
        data = context.buffer.peek(5)
        if len(data) < 4:
            raise EndOfDataException("Not enough data to parse JSON encoding.")
        
        if data[:1] == b'\x66':
            if len(data) < 5:
                raise EndOfDataException("Not enough data to parse JSON false.")
            if data[1:5] == b'\x61\x6c\x73\x65':
                context._apply_value(False)
                context.buffer.read(5)
                context._next_state(JsonParsingMeta)
                return
        elif data[:1] == b'\x6e':
            if len(data) < 4:
                raise EndOfDataException("Not enough data to parse JSON null.")
            if data[1:4] == b'\x75\x6c\x6c':
                context._apply_value(None)
                context.buffer.read(4)
                context._next_state(JsonParsingMeta)
                return
        elif data[:1] == b'\x74':
            if len(data) < 4:
                raise EndOfDataException("Not enough data to parse JSON true.")
            if data[1:4] == b'\x72\x75\x65':
                context._apply_value(True)
                context.buffer.read(4)
                context._next_state(JsonParsingMeta)
                return
        
        raise UnsupportedFormatException("Not a valid JSON constant.")

class JsonParsingMeta(JsonParsingState):
    def parse_data(self, context: PObjParser):
        data = context.buffer.peek(1)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON meta.")
        
        if data[:1] in b'\x09\x0a\x0d\x20':
            context._next_state(JsonParsingWhitespace)
            return

        if data[:1] in b'\x66\x6e\x74':
            context._next_state(JsonParsingConstant)
            return

        if data[:1] in b'\x2d\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39':
            context._next_state(JsonParsingNumber)
            return

        if data[:1] == b'\x22':
            context._next_state(JsonParsingString)
            return

        if data[:1] == b'\x3a':
            context.buffer.read(1)
            return
        
        if data[:1] == b'\x5b':
            context._start_array()
            context.buffer.read(1)
            return
        
        if data[:1] == b'\x7b':
            context._start_map()
            context.buffer.read(1)
            return

        if data[:1] in b'\x5d\x7d':
            context._end_container()
            context.buffer.read(1)
            return

        raise UnsupportedFormatException(f"Not a valid JSON meta character: {data[:1]}")

class JsonParsingStart(JsonParsingState):

    VALID_BYTES = b'\x09\x0a\x0d\x20\x22\x2d\x30-\x39\x5b\x5d\x66\x6e\x74\x7b\x7d'

    def parse_data(self, context: PObjParser):
        data = context.buffer.peek(2)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON encoding.")
        if not data[:1] in JsonParsingStart.VALID_BYTES or data[1] == b'\x00':
            raise UnsupportedFormatException("Not a valid UTF-8 Encoded JSON")
        
        context._next_state(JsonParsingMeta)

class JsonParser(PObjParser):

    @staticmethod
    def match_extension(buffer: PObjBuffer):
        if not buffer.meta['fname']:
            return False
        for ext in ['.json']:
            if buffer.meta['fname'].endswith(ext):
                return True
        return False

    @staticmethod
    def match_magic(buffer: PObjBuffer):
        return False

    
    def __init__(self, parent: PObjBuffer, id: str):
        super().__init__(parent, id)
        self.state: Optional[JsonParsingState] = JsonParsingStart()

        self.num_bytes = []
        self.str_bytes = ['"']

        self.json_ref = None
        self.current = None
        self.stack = []
        self.key_reg = None

    def _next_state(self, state: JsonParsingState):
        self.state = state()

    def _apply_value(self, value):
        if self.key_reg:
            self.current[self.key_reg] = value
            self.key_reg = None
        elif isinstance(self.current, list):
            self.current.append(value)
        elif isinstance(self.current, dict) and self.key_reg == None:
            self.key_reg = value
        else:
            self.current = value
            self.meta['root'] = self.current
    
    def _start_map(self):
        self.stack.append(self.current)
        if self.key_reg:
            self.current[self.key_reg] = {}
            self.current = self.current[self.key_reg]
            self.key_reg = None
        elif isinstance(self.current, list):
            self.current.append({})
            self.current = self.current[-1]
        else:
            self.current = {}
            self.meta['root'] = self.current

    def _start_array(self):
        self.stack.append(self.current)
        if self.key_reg:
            self.current[self.key_reg] = []
            self.current = self.current[self.key_reg]
            self.key_reg = None
        elif isinstance(self.current, list):
            self.current.append([])
            self.current = self.current[-1]
        else:
            self.current = []
            self.meta['root'] = self.current

    def _end_container(self):
        if len(self.stack) > 1:
            self.current = self.stack.pop()
            self.meta['root'] = self.current
    
    def process_data(self):

        exc_store = None
        try:
            while True:
                self.state.parse_data(self)
        except EndOfDataException as e:
            if not exc_store:
                exc_store = e
        except UnsupportedFormatException:
            raise

        for child in self.children:
            try:
                child.process_data()
            except EndOfDataException as e:
                if not exc_store:
                    exc_store = e
        
        if exc_store:
            raise exc_store

        return self

    

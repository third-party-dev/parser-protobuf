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

from thirdparty.pparse.lib import EndOfDataException, UnsupportedFormatException
import thirdparty.pparse.lib as pparse
#from thirdparty.pparse.lib import Range, Node, Cursor, Data, Parser, Artifact


'''
Roles:
- **Data** points to _data source_ (i.e. a shared file descriptor).
- **Reader** is something that can tell, seek, skip, peek, read, and dup.
- **Cursor** is an unbounded offset into a data source (isa Reader).
- **Range** has start, cursor, and length of data source (isa Reader)
- **Extraction** is _named_ range of data to link with Parsers.
- **pparse** generates (initial) **Extraction** from **Data**
- **pparse** discovers and assigns **Parsers** to **Extractions**
- **Parser** parses data as node tree within parser associated Extraction.
  - Do we keep parser state when complete? (I think no.)
- **Parsers** generate sub-Extractions from Extraction
- Sub-**Extraction** stored in parent **Extraction**
  - Sub-**Extraction** may point to node (must be strong reference?).

Nodes are dumb:
- Each node has (at most) 4 references: start, length, meta, _data_.
- Point to start and length of data (but **not** the data).
- `meta` is None when parser is done with Node.
- _data_ is node sub-type specific ({} for Map, [] for Array)
- Depends on Parser for all processing. (i.e. its state for Parser)
- State or Data Type of the Node is implicit in the Node subclass.

Parsers and their Node trees are tightly coupled.
The parser and node tree are linked by the Extraction object.

Different Format Approaches To Consider:
- JSON is not length delimited, therefore must be **depth-first**.
- Protobuf is length delimited, can be breadth first.

- Flexbuffers/Flatbuffers - oob tables, may require non-continugous ranges.
- Flexbuffers - Length delimited, bottom up. (Leaves parsed first.)
- Flatbuffers - Length delimited, top down. (Ancestors parsed first.)

'''




class JsonParsingState(object):
    def parse_data(self, parser: 'JsonParser', node):
        raise NotImplementedError()


class JsonParsingNumber(JsonParsingState):
    def __init__(self):
        self.num_bytes = []

    def parse_data(self, parser: 'JsonParser', node):
        data = node.peek(0x400)
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
            self.num_bytes.append(data[offset:offset+1])
            offset += 1
        node.read(offset)

        if done:
            try:
                node._apply_node_value(parser, json.loads(b''.join(self.num_bytes)))
            except Exception as e:
                raise UnsupportedFormatException(f"Invalid number format in {self.num_bytes}: {e}")
            finally:
                self.num_bytes = []
            
        node._next_state(JsonParsingMeta)


class JsonParsingString(JsonParsingState):
    def __init__(self):
        self.str_bytes = [b'\x22']

    def parse_data(self, parser: 'JsonParser', node):
        data = node.peek(0x400)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse JSON string.")

        offset = 0
        while offset < len(data) and len(data) - offset > 1:
            if data[offset:offset+1] == b'\x22':
                # We're done
                try:
                    self.str_bytes.append(node.read(offset+1))
                    node._apply_node_value(parser, json.loads(b''.join(self.str_bytes)))
                except Exception as e:
                    raise UnsupportedFormatException(f"Invalid string format in {self.str_bytes}: {e}")
                finally:
                    self.str_bytes = [b'"']
                
                node._next_state(JsonParsingMeta)
                return
        
            elif data[offset:offset+1] == b'\x5c':
                if data[offset+1:offset+2] == b'\x75':
                    if len(data) < 6:
                        raise EndOfDataException("Not enough bytes to parse JSON enicode char in string.")
                    self.str_bytes.append(data[offset:offset+6])
                    offset += 6
                    continue
                if data[offset+1] in b'\x22\x5c\x2f\x62\x66\x6e\x72\x74':
                    self.str_bytes.append(data[offset:offset+2])
                    offset += 2
                    continue

            else:
                offset += 1
        
        self.str_bytes.append(node.read(offset))


class JsonParsingWhitespace(JsonParsingState):
    def parse_data(self, parser: 'JsonParser', node):
        data = node.peek(0x400)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON whitespace.")
        
        offset = 0
        while offset < len(data):
            if not data[offset:offset+1] in b'\x09\x0a\x0d\x20':
                break
            offset += 1
        node.skip(offset)

        node._next_state(JsonParsingMeta)


class JsonParsingConstant(JsonParsingState):
    def parse_data(self, parser: 'JsonParser', node):
        data = node.peek(5)
        if len(data) < 4:
            raise EndOfDataException("Not enough data to parse JSON encoding.")
        
        if data[:1] == b'\x66':
            if len(data) < 5:
                raise EndOfDataException("Not enough data to parse JSON false.")
            if data[1:5] == b'\x61\x6c\x73\x65':
                node._apply_node_value(parser, False)
                node.skip(5)
                node._next_state(JsonParsingMeta)
                return
        elif data[:1] == b'\x6e':
            if len(data) < 4:
                raise EndOfDataException("Not enough data to parse JSON null.")
            if data[1:4] == b'\x75\x6c\x6c':
                node._apply_node_value(parser, None)
                node.skip(4)
                node._next_state(JsonParsingMeta)
                return
        elif data[:1] == b'\x74':
            if len(data) < 4:
                raise EndOfDataException("Not enough data to parse JSON true.")
            if data[1:4] == b'\x72\x75\x65':
                node._apply_node_value(parser, True)
                node.skip(4)
                node._next_state(JsonParsingMeta)
                return
        
        raise UnsupportedFormatException("Not a valid JSON constant.")


class JsonParsingMeta(JsonParsingState):
    WHITESPACE_BYTES = b'\x09\x0a\x0d\x20'
    CONSTANT_BYTES = b'\x66\x6e\x74'
    NUMBER_BYTES = b'\x2d\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39'
    COLON_COMMA = b'\x3a\x2c'
    DOUBLE_QUOTE = b'\x22'
    LEFT_BRACKET = b'\x5b'
    LEFT_CURLY = b'\x7b'
    RIGHT_BRACKET_CURLY = b'\x5d\x7d'

    def parse_data(self, parser: 'JsonParser', node):
        data = node.peek(1)
        if len(data) < 1:
            raise EndOfDataException(f"Not enough data to parse JSON meta. Offset: {node.tell()}")

        if data[:1] in JsonParsingMeta.WHITESPACE_BYTES:
            node._next_state(JsonParsingWhitespace)
            return

        if data[:1] in JsonParsingMeta.CONSTANT_BYTES:
            node._next_state(JsonParsingConstant)
            return

        if data[:1] in JsonParsingMeta.NUMBER_BYTES:
            node._next_state(JsonParsingNumber)
            return

        if data[:1] == JsonParsingMeta.DOUBLE_QUOTE:
            node.skip(1)
            node._next_state(JsonParsingString)
            return

        if data[:1] in JsonParsingMeta.COLON_COMMA:
            node.skip(1)
            return
        
        # ----- structure stuff -----

        if data[:1] == JsonParsingMeta.LEFT_BRACKET:
            node.skip(1)
            node._start_array_node(parser)
            return
        
        if data[:1] == JsonParsingMeta.LEFT_CURLY:
            node.skip(1)
            node._start_map_node(parser)
            return

        if data[:1] in JsonParsingMeta.RIGHT_BRACKET_CURLY:
            node.skip(1)
            node._end_container_node(parser)
            return

        raise UnsupportedFormatException(f"Not a valid JSON meta character: {data[:1]}")


class JsonParsingStart(JsonParsingState):

    VALID_BYTES = b'\x09\x0a\x0d\x20\x22\x2d\x5b\x5d\x66\x6e\x74\x7b\x7d' \
        b'\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39'

    def parse_data(self, parser: 'JsonParser', node):
        data = node.peek(2)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON encoding.")
        if not data[:1] in JsonParsingStart.VALID_BYTES or data[1] == b'\x00':
            raise UnsupportedFormatException("Not a valid UTF-8 Encoded JSON")
        
        node._next_state(JsonParsingMeta)


'''
I feel like this code base is 33% there. I've now successfully broken up the 
main loop code from the actual node tree that does the parsing. The current 
issue is we don't have a way for the nodes to parse themselves in isolation
from the rest of the tree.

Ideally, the nodes will minimize the state that they keep about themselves:

- Reader - Initially Cursor, Range when length known.
  - A Range gets us start, end, and length.
  - Keeping Range in temporary and only saving start and end saves a reference.
    The parser has the artifact and therefore the Data object we'd used to
    generate the Range.
- State - TODO: State should be inferred by type.

- Temporary meta for runtime parsing, should be reclaimed when done.
  - All temporary data could be kept in a Node.temp dictionary.
  - Parent - required for rewinding while parsing
    - Parent references can be used for ref counting, but no concern now.
  - Key-reg - Nodes only need key reg when building map entries
  - child - A weird one only used by root... need a new LazyJsonParserRootNode
  - value - Need a new LazyJsonParser{TYPE}Node

Nodes have states: scanning -> shelf -> parsing -> loaded -> shelf -> ...
'''


class LazyJsonParserNode():
 
    def __init__(self, parent, reader: pparse.Reader):
        self._state: Optional[JsonParsingState] = JsonParsingStart()
        self._parent = parent # Parent Node (None for root)
        self._reader = reader.dup()
        self._start = self.tell()
        self._end = None
        
        # If we're in a map, indicates if a key & what the key is.
        self.key_reg = None

        self.value = None

        self.child = None


    def state(self):
        return self._state


    def _next_state(self, state: JsonParsingState):
        self._state = state()


    def reader(self):
        return self._reader


    def mark_end(self):
        self._end = self.reader().tell()


    # Convienence Aliases
    def tell(self):
        return self._reader.tell()
    def seek(self, offset):
        return self._reader.seek(offset)
    def skip(self, length):
        return self._reader.skip(length)
    def peek(self, length):
        return self._reader.peek(length)
    def read(self, length, mode=None):
        return self._reader.read(length, mode=mode)



    def _apply_node_value(self, parser, value):
        if self.key_reg:
            if isinstance(value, str) and len(value) > 40:
                print(f"apply_val: Inside map, unset keyreg, skipping set value")
                pass
            else:
                print(f"apply_val: Inside map, unset keyreg, set value ({value})")
                parser.current.map[self.key_reg] = value
            self.key_reg = None
        elif isinstance(parser.current, LazyJsonParserArrayNode):
            print(f"apply_val: Inside arr, append value ({value})")
            parser.current.arr.append(value)
        elif isinstance(parser.current, LazyJsonParserMapNode) and self.key_reg == None:
            print(f"apply_val: Inside map, setting key reg ({value})")
            self.key_reg = value
        else:
            print(f"apply_val: Top level, set value ({value})")
            # Note: When top level is scalar.
            parser.current.value = value

    
    def _start_map_node(self, parser):
        
        newmap = LazyJsonParserMapNode(parser.current, self.reader())
        
        if self.key_reg:
            print("start_map: Found key, assuming in Map. Add new map to current map.")
            parser.current.map[self.key_reg] = newmap
            parser.current = parser.current.map[self.key_reg]
            self.key_reg = None
        elif isinstance(parser.current, LazyJsonParserArrayNode):
            print("start_map: Inside Array. Append new map to current array.")
            parser.current.arr.append(newmap)
            parser.current = newmap
        else:
            print("start_map: Create map as top level object.")
            parser.current.child = newmap
            parser.current = newmap


    def _start_array_node(self, parser):
        
        newarr = LazyJsonParserArrayNode(parser.current, self.reader())

        if self.key_reg:
            print("start_arr: Found key, assuming in Map. Add new arr to current map.")
            parser.current.map[self.key_reg] = newarr
            parser.current.child = newarr
            parser.current = parser.current.map[self.key_reg]
            self.key_reg = None
        elif isinstance(parser.current, LazyJsonParserArrayNode):
            print("start_arr: Inside Array. Append new arr to current array.")
            parser.current.arr.append(newarr)
            parser.current.child = newarr
            parser.current = newarr
        else:
            print("start_arr: Create arr as top level object.")
            parser.current.child = newarr
            parser.current = newarr


    def _end_container_node(self, parser):
        if self._parent:
            print("end_container: Backtracking to parent.")
            parser.current.mark_end()
            self._parent.seek(self._end)
            parser.current = self._parent

# artifact.candidates['json']['meta']['root'].child.map

class LazyJsonParserMapNode(LazyJsonParserNode):
    def __init__(self, parent, reader: pparse.Reader):
        super().__init__(parent, reader)
        self.map = {}
    
    def __repr__(self):
        return f"MAP({self.map})"




class LazyJsonParserArrayNode(LazyJsonParserNode):
    def __init__(self, parent, reader: pparse.Reader):
        super().__init__(parent, reader)
        self.arr = []
    
    def __repr__(self):
        return f"ARRAY({self.arr})"











class LazyJsonParser(pparse.Parser):

    @staticmethod
    def match_extension(fname: str):
        if not fname:
            return False
        for ext in ['.json']:
            if fname.endswith(ext):
                return True
        return False


    @staticmethod
    def match_magic(cursor: pparse.Cursor):
        return False

    
    def __init__(self, artifact: pparse.Artifact, id: str):
        super().__init__(artifact, id)
        
        # Current reference of thing being parsed.
        self._meta['root'] = LazyJsonParserNode(None, self.reader())
        # Current path of pending things.
        self.current = self._meta['root']

    
    def eagerly_parse(self):

        exc_store = None
        try:
            #breakpoint()
            #print(f"{self.state}.parse_data()")
            while True:
                self.current.state().parse_data(self, self.current)
        except EndOfDataException as e:
            if not exc_store:
                exc_store = e
        except UnsupportedFormatException:
            raise

        for child in self.children:
            try:
                child.scan_data()
            except EndOfDataException as e:
                if not exc_store:
                    exc_store = e
        
        if exc_store:
            raise exc_store

        return self


    def scan_data(self):
        return self.eagerly_parse()
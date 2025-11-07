#!/usr/bin/env python3

import os
from pprint import pprint

from typing import Optional
from thirdparty.pparse.utils import has_mmap, mmap, hexdump

PARSERS = {}

class EndOfDataException(Exception): pass
class UnsupportedFormatException(Exception): pass
class BufferFullException(Exception): pass


# Range manages length.
# Cursor does not manage length.
# Data does not manage offset.
class Range():
    # Given Cursor object is the start offset
    def __init__(self, cursor, length:int):
        self._start_cursor = cursor.dup()
        self._start = self._start_cursor.tell()
        self._cursor = cursor.dup()
        if length < 0:
            raise ValueError("length < 0")
        # Consider: Check for length beyond data?
        self._length = length
        self._end = self._start + length


    def length(self):
        return self._length

    def left(self):
        return self._end - self.tell()

    def valid_offset(self, offset):
        return offset >= self._start and offset < self._end


    def dup(self):
        return Range(self._start_cursor, self._length)


    def tell(self):
        return self._cursor.tell()


    # Set cursor to specific location.
    def seek(self, offset):
        if not self.valid_offset(offset):
            raise ValueError(f"Offset ({offset}) out of bounds.")
        self._cursor.seek(offset)


    def _check_adjust_length(self, length, throw:bool=False):
        if length < 0:
            if throw:
                raise ValueError("length < 0")
            return self.tell()
        
        offset = self.tell() + length
        if not self.valid_offset(offset):
            if throw:
                raise ValueError(f"Offset ({offset}) out of bounds.")
            length = self._end - self.tell()
        
        return length


    def skip(self, length, throw:bool=False):
        length = self._check_adjust_length(length, throw)
        return self._cursor.skip(length)


    # Read data ahead without progressing cursor.
    def peek(self, length, throw:bool=False):
        length = self._check_adjust_length(length, throw)
        return self._cursor.peek(length)


    # Copy and progress data.
    def read(self, length, throw:bool=False, mode=None):
        length = self._check_adjust_length(length, throw)
        return self._cursor.read(length, mode=mode)

    

class Node():
    def __init__(self):
        # TODO: Implement
        raise NotImplementedError("Node class not implemented.")

    def parents(self): #-> [Node]:
        pass

    def children(self): # -> [weakref(Node)] -> Return array of childen (weak refs).
        # - Triggers parse/load
        pass

    def attributes(self) -> dict:  # - Return dictionary of attributes.
        # - Triggers parse/load
        pass

    def child(self, index=-1): # -> Node: # - Return strong ref child.
        # - Triggers parse/load
        pass

    #def as_{bytes,i64,u64,str}() - Cast raw data as type.
    #- Triggers parse/load

    def loaded(self): # - Is the data loaded and parsed?
        pass


    def range(self): # - A range of data this node covers.
        pass


# Cursor manages offset. Data does not manage offset.
class Cursor():
    def __init__(self, data, offset=0):
        self._data = data
        self._offset = offset


    def dup(self):
        return self._data.open(self._offset)


    # Where in the Data are we
    def tell(self):
        return self._offset


    # Set cursor to specific location.
    def seek(self, offset):
        self._offset = offset
        return self._data.seek(self)
        

    def skip(self, length):
        self._offset += length
        return self._data.seek(self)


    # Read data ahead without progressing cursor.
    def peek(self, length):
        return self._data.peek(self, length)


    # Copy and progress data.
    def read(self, length, mode=None):
        data = self._data.read(self, length, mode=mode)
        self._offset += len(data)
        return data
        

# Data Considerations:
# - DiskData exists in its entirety on disk (even if truncated).
# - TapeData is constantly incoming and recorded (yes to Random Access).
#   - Need to re-mmap when data is appended.
# - StreamData is constantly incoming and only seen once (no to Random Access).

# StreamData may require entire stream to exist in memory, depending on parser
# references. A StreamData buffer can only deallocate data when all parsers
# have indicated they have no more need for the data range.


# Data manages mmap and fobj. Cursor does not manage mmap or fobj.
class Data():

    MODE_READ = 1
    MODE_MMAP = 2

    def __init__(self, path=None, mode=None):
        if mode is None:
            self._mode = Data.MODE_READ
        else:
            self._mode = mode
        
        if not path or not os.path.exists(path):
            raise ValueError("path must be a string that points to a valid file path")

        # TODO: Only allow setting MODE_MMAP if has_mmap()

        self._path = path

        # One descriptor to rule them all.
        self._fobj = open(path, "rb")

        # # TODO: This size is only relevant if the size doesn't change.
        # fd = self._fobj.fileno()
        # st = os.fstat(fd)
        # self.length = -1
        # if stat.S_ISREG(st.st_mode):
        #     self.length = st.st_size

        # Mmap, if available.
        if has_mmap():
            self._mmap = mmap.mmap(self._fobj.fileno(), 0, access=mmap.ACCESS_READ)
            self._mem = memoryview(self._mmap)

    
    def mode(self):
        return self._mode


    # Create a cursor, like a logical file descriptor.
    def open(self, offset=0):
        return Cursor(self, offset)


    # Read data ahead without progressing cursor.
    def peek(self, cursor, length, mode=None):
        # TODO: Only allow setting MODE_MMAP if has_mmap()
        # Allow each read to optionally override mode.
        active_mode = self.mode()
        if mode:
            active_mode = mode
        
        if active_mode == Data.MODE_READ:
            self._fobj.seek(cursor.tell(), os.SEEK_SET)
            return self._fobj.read(length)

        if active_mode == Data.MODE_MMAP and has_mmap():
            off = cursor.tell()
            return self._mem[off:off+length]


    # Progress cursor without reading (no copy).
    def seek(self, cursor) -> None:
        if self.mode() == Data.MODE_READ:
            self._fobj.seek(cursor.tell(), os.SEEK_SET)
        # Noop for mmap.
        return cursor.tell()
        

    # Read the data.
    def read(self, cursor, length, mode=None):
        # TODO: Only allow setting MODE_MMAP if has_mmap()
        # Allow each read to optionally override mode.
        active_mode = self.mode()
        if mode:
            active_mode = mode
    
        if active_mode == Data.MODE_READ:
            self.seek(cursor)
            return self._fobj.read(length)

        if active_mode == Data.MODE_MMAP and has_mmap():
            off = cursor.tell()
            return self._mem[off:off+length]


'''
    Parser Considerations:

    It is the parser's responsibility to be lazy. The framework will allow a parser to
    attempt to scan over the data within its scope. The parser can choose to do all of
    the parsing in this phase, or ramain willfully ignorant of the data until the user
    references the data.

    It is difficult to anticipate the types of references that all interfaces would
    require. Therefore its also the parser's responsibility to implement the lookup
    API for the data within its scope. Parsers must use the framework's children member
    to advertise data that it is not willing or able to parse (e.g. another file within
    a zip container).

    It may be possible to implement an 80% solution API for referencing data in a generic
    way. The idea is that all data should be representable in a graph and you'd string
    together references to create a generic path to access any given information in the
    graph. In the generic data graph we'd have nodes that have children nodes and attributes.
    An API might resemble:

    - Node.parents() -> [Node] -> Return array of parents (strong refs).
    - Node.children() -> [weakref(Node)] -> Return array of childen (weak refs).
    - Triggers parse/load
    - Node.attributes() -> {} - Return dictionary of attributes.
    - Triggers parse/load
    - Node.child(index=-1) -> Node - Return strong ref child.
    - Triggers parse/load
    - Node.as_{bytes,i64,u64,str}() - Cast raw data as type.
    - Triggers parse/load
    - Node.loaded() - Is the data loaded and parsed?
    - Node.range() - A range of data this node covers.
    - Note: There could be situations where a conceptual "Node" is a non-continguous
            set of ranges in the data. Joining non-continguous sections of data into
            a cohesive object is not the responsibility of the parser or framework.
            That responsibility should fall to a higher level framework or code base.
    - Note: There should be nothing preventing nodes from overlapping. Its is the parsers
            responsibility to manage that situation and be aware that readahead
            optimizations will break when moving backward in memory.

    If all the child references were weakref. As long as there is a strong reference to
    the child, its path will remain. 

    All nodes should be either in a loaded state or unloaded state. In the loaded state
    they are fully cached and dereference-able. In the unloaded state, the node is only
    a cursor into the data to be parsed.

    Note: When processing a large JSON object or array, all of the data needs to be
    read and parsed to know where the end of the object is and all of its immediate
    children.

    When scanning a file or Artifact, parse entire file to tracking size of:
    - What are the sizes of strings and serialized arrays of primatives?
    - What is the memory footprint of the data structure up to leaf nodes?
'''

# Base Parser for Artifact parsers.
class Parser(dict):

    def __init__(self, artifact, id: str):
        if not isinstance(artifact, Artifact):
            raise TypeError("artifact must be an Artifact")
        
        # parser id
        self._id: str = id

        # parent artifact
        self._artifact = artifact

        # cursor to read data
        self._cursor = artifact.dup_cursor()

        # child artifacts
        self._meta: dict = { 'children': [] }
        self.children: list = self._meta['children']

        # Setup as dict for easy repr
        dict.__init__(self, meta=self._meta)


    def cursor(self):
        return self._cursor

    def range(self, length):
        return Range(self._cursor, length)

    # Convienence Aliases
    def tell(self):
        return self._cursor.tell()
    def seek(self, offset):
        return self._cursor.seek(offset)
    def skip(self, length):
        return self._cursor.skip(length)
    def peek(self, length):
        return self._cursor.peek(length)
    def read(self, length, mode=None):
        return self._cursor.read(length, mode=mode)

    # TODO: left() - How many bytes before we run out?
    # TODO: size() - How many bytes is the artifact?


    # This processes all data at once.
    # TODO: What is the interface that only parses what we need to?   
    def scan_data(self):
        raise NotImplementedError()
    

    @staticmethod
    def match_extension(fname):
        return False
    

    @staticmethod
    def match_magic(cursor):
        return False


# Generic artifact that ties parsers to cursor-ed data.
class Artifact(dict):
    def __init__(self, cursor, parser: Optional['Parser'] = None):
        self._parser: Optional['Parser'] = parser
        # This cursor is only used for dup() and tell()
        self._cursor = cursor

        self._meta = {
            'fname': None,
            'candidates': {},
        }

        # Candidate parsers.
        self.candidates: dict = self._meta['candidates']
        # Setup as dict for easy repr
        dict.__init__(self, meta=self._meta)
    

    def get_fname(self):
        return self._meta['fname']


    def set_fname(self, name):
        self._meta['fname'] = name
        return self

    
    def dup_cursor(self):
        return self._cursor.dup()


    # This processes all data at once.
    # TODO: What is the interface that only parses what we need to?    
    def scan_data(self):
        global PARSERS

        for (pname, parser) in PARSERS.items():
            if pname not in self.candidates:
                if parser.match_extension(self.get_fname()):
                    self.candidates[pname] = parser(self, pname)
                    continue
                if parser.match_magic(self.dup_cursor()):
                    self.candidates[pname] = parser(self, pname)
                    continue
            
        for (cname, candidate) in self.candidates.items():
            candidate.scan_data()

        return self



    


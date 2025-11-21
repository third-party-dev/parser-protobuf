import sys
import os

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.zip.node import NodeArray
from thirdparty.pparse.lazy.zip.state import ZipParsingMagic


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

def trace(*args, **kwargs):
    print(*args, **kwargs)
    pass


class Parser(pparse.Parser):

    @staticmethod
    def match_extension(fname: str):
        if not fname:
            return False
        for ext in ['.zip']:
            if fname.endswith(ext):
                return True
        return False


    @staticmethod
    def match_magic(cursor: pparse.Cursor):
        return False

    
    def __init__(self, source: pparse.Extraction, id: str):
        super().__init__(source, id)
        
        # Fundamentally, zip is an array of files.
        self.current = NodeArray(None, source.open())
        self.current.ctx()._next_state(ZipParsingMagic)
        source._result[id] = self.current


    def _end_container_node(self, ctx):
        parent = ctx._parent
        if parent:
            trace(f"end_container (off:{ctx.tell()}): Backtracking to parent.")

            # Set the end pointer to advance parent past field.
            ctx.mark_end()

            # Fast forward past the bit we just parsed.
            parent.ctx().seek(ctx._end)

            # Kill ctx (hopefully reclaiming memory).
            ctx.node().clear_ctx()

            # Set current node to parent.
            self.current = parent

    
    def scan_data(self):

        # While not end of data, keep parsing via states.
        try:
            while True:
                self.current.ctx().state().parse_data(self, self.current.ctx())
        except pparse.EndOfNodeException as e:
            pass
        except pparse.EndOfDataException as e:
            pass
        except pparse.UnsupportedFormatException:
            raise

        # TODO: Do all the children.
        
        return self
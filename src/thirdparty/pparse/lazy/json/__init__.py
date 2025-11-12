import sys
import os

from thirdparty.pparse.lib import (
    EndOfDataException,
    UnsupportedFormatException,
    EndOfNodeException
)
import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.json.node import (
    Node,
    NodeContext,
    NodeInit,
    NodeMap,
    NodeArray
)


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
    #print(*args, **kwargs)
    pass


class Parser(pparse.Parser):

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

    
    def __init__(self, source: pparse.Extraction, id: str):
        super().__init__(source, id)
        
        # Current path of pending things.
        self.current = NodeInit(None, source.open(), self)
        source._result[id] = self.current


    def _apply_node_value(self, ctx: NodeContext, value):
        if ctx.key():
            # if isinstance(value, str) and len(value) > 40:
            #     trace(f"apply_val: Inside map, unset keyreg, skipping set value")
            #     # At this point, we've already parsed the string, now we'll let it go.
            #     parent = self.current
            #     length = ctx.tell() - ctx.field_start()
            #     reader = ctx.reader()
            #     reader.seek(ctx.field_start())
            #     range = pparse.Range(reader, length)
            #     self.current.value[ctx.key()] = Node(parent, range)
            # else:
            trace(f"apply_val: Inside map, unset keyreg, set value ({value})")
            self.current.value[ctx.key()] = value

            ctx.set_key(None)
        elif isinstance(self.current, NodeArray):
            trace(f"apply_val: Inside arr, append value ({value})")
            self.current.value.append(value)
        elif isinstance(self.current, NodeMap) and ctx.key() is None:
            trace(f"apply_val: Inside map, setting key reg ({value})")
            ctx.set_key(value)
        else:
            trace(f"apply_val: Top level or on-demand loading, set value ({value})")
            #breakpoint()
            self.current.value = value

    
    def _start_map_node(self, ctx):
        
        parent = self.current
        # BUG: When we get a cursor, we're getting a duplicate of the cursor and its _current_ offset.
        # BUG: When we get a range, we're getting a duplicate of the range with the original offset?!
        newmap = NodeMap(parent, ctx.reader())
        newmap.ctx().skip(1)
        
        if ctx.key():
            trace(f"start_map (off:{ctx.tell()}): Found key, assuming in Map. Add new map to current map.")
            parent.value[ctx.key()] = newmap
            self.current = parent.value[ctx.key()]
            ctx.set_key(None)
        elif isinstance(self.current, NodeArray):
            trace(f"start_map (off:{ctx.tell()}): Inside Array. Append new map to current array.")
            self.current.value.append(newmap)
            self.current = newmap
        else:
            trace(f"start_map (off:{ctx.tell()}): Create map as top level object.")
            parent.value = newmap
            self.current = newmap


    def _start_array_node(self, ctx):
        
        newarr = NodeArray(self.current, ctx.reader())
        newarr.ctx().skip(1)

        if ctx.key():
            trace(f"start_arr (off:{ctx.tell()}): Found key, assuming in Map. Add new arr to current map.")
            self.current.value[ctx.key()] = newarr
            self.current = self.current.value[ctx.key()]
            ctx.set_key(None)
        elif isinstance(self.current, NodeArray):
            trace(f"start_arr (off:{ctx.tell()}): Inside Array. Append new arr to current array.")
            self.current.value.append(newarr)
            self.current = newarr
        else:
            trace(f"start_arr (off:{ctx.tell()}): Create arr as top level object.")
            self.current = newarr


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
        # else:
        #     trace("end_container: Backtracking to initial node.")

        #     # Set the end pointer to advance parent past field.
        #     ctx.mark_end()

        #     # Kill ctx (hopefully reclaiming memory).
        #     ctx.node().clear_ctx()
            

    
    def scan_data(self):

        # While not end of data, keep parsing via states.
        try:
            while True:
                #                                    (parser, ctx )
                self.current.ctx().state().parse_data(self,   self.current.ctx())
        except EndOfNodeException as e:
            pass
        except EndOfDataException as e:
            pass
        except UnsupportedFormatException:
            raise

        # TODO: Do all the children.
        
        return self
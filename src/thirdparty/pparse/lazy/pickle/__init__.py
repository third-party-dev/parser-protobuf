#!/usr/bin/env python3

import sys
import os
import io
from typing import Optional

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.pickle.opnodes import NodePickleArray
from thirdparty.pparse.lazy.pickle.opstates import PickleParsingPickleStream


def trace(*args, **kwargs):
    print(*args, **kwargs)
    pass


class Parser(pparse.Parser):

    @staticmethod
    def match_extension(fname: str):
        if not fname:
            return False
        #for ext in ['.onnx']:
        for ext in ['.pkl']:
            if fname.endswith(ext):
                return True
        return False


    @staticmethod
    def match_magic(cursor: pparse.Cursor):
        return False

    
    def __init__(self, source: pparse.Extraction, id: str):
        super().__init__(source, id)

        self.current = NodePickleArray(None, source.open())
        self.current.ctx()._next_state(PickleParsingPickleStream)
        source._result[id] = self.current


    def _end_container_node(self, ctx):
        parent = ctx._parent
        if parent:
            trace(f"end_container (off:{ctx.tell()}): Backtracking to parent {parent}.")

            # Set the end pointer to advance parent past field.
            ctx.mark_end()

            # In parent, fast forward past the bit we just parsed.
            parent.ctx().seek(ctx._end)

            # Kill ctx (hopefully reclaiming memory).
            ctx.node().clear_ctx()

            # Set current node to parent.
            self.current = parent

    
    def scan_data(self):

        # Do the opcodes first.
        try:
            while True:
                # While not end of data, keep parsing via states.
                self.current.ctx().state().parse_data(self, self.current.ctx())
        except pparse.EndOfNodeException as e:
            pass
        except pparse.EndOfDataException as e:
            pass
        except pparse.UnsupportedFormatException:
            raise


        # TODO: Do all the children.
        
        return self

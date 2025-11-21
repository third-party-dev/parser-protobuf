#!/usr/bin/env python3

import struct
from pprint import pprint

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.pickle.meta import PklOp
from thirdparty.pparse.lazy.pickle.opnodes import NodePickleArray, NodePickle


def trace(*args, **kwargs):
    print(*args, **kwargs)
    pass


class PickleParsingState():
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        raise NotImplementedError()


class PickleParsingReadlineParam(PickleParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        op = ctx.current_op
        data = ctx.peek(0x4000)
        if not data or len(data) < 1:
            raise pparse.EndOfDataException("Not enough data to parse readline delimited pickle opcode")
        
        # Do we have a newline?
        # TODO: We *should* be more tolerant of very large parameters here.
        offset = data.find(b'\n')
        if offset == -1:
            raise pparse.EndOfDataException("Not enough data to find end of readline delimited pickle opcode")

        if op.opcode == PklOp.GLOBAL and op.param != None:
            op.param2 = data[0:offset+1]
            ctx.skip(offset+1)
            ctx._next_state(PickleInterpreter)
            return

        op.param = data[0:offset+1]
        ctx.skip(offset+1)
        if op.opcode == PklOp.GLOBAL:
            # Keep going.    
            return
        ctx._next_state(PickleInterpreter)


class PickleParsingSimpleParam(PickleParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        op = ctx.current_op
        data = ctx.peek(op.pbytes)
        if not data or len(data) < op.pbytes:
            raise pparse.EndOfDataException("Not enough data to parse simple pickle opcode")

        op.param = struct.unpack(op.fmt, data)[0]
        ctx.skip(op.pbytes)
        ctx._next_state(PickleInterpreter)


class PickleParsingLengthParam(PickleParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        op = ctx.current_op
        data = ctx.peek(op.byte_len)
        if not data or len(data) < op.byte_len:
            raise pparse.EndOfDataException("Not enough data to parse simple pickle opcode")

        op.param = data[0:op.byte_len]
        ctx.skip(op.byte_len)
        ctx._next_state(PickleInterpreter)


class PickleParsingLengthPrefix(PickleParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        op = ctx.current_op
        data = ctx.peek(op.lbytes)
        if len(data) < op.lbytes:
            raise pparse.EndOfDataException("Not enough data to parse simple pickle opcode")

        op.byte_len = struct.unpack(op.fmt, data[0:op.lbytes])[0]
        ctx.skip(op.lbytes)
        ctx._next_state(PickleParsingLengthParam)


class StackMark():
    def __init__(self, opcode):
        self.opcode = opcode

    def __repr__(self):
        return '**MARK**'

class PersistentCall():
    def __init__(self, id, arg, opcode):
        self.id = id
        self.arg = arg
        self.opcode = opcode
    
    def __repr__(self):
        return '**PERSID CALL**'

class ReduceCall():
    def __init__(self, module_call, arg, opcode):
        self.module_call = module_call
        self.arg = arg
        self.opcode = opcode

    def __repr__(self):
        return '**REDUCE CALL**'


class PickleInterpreter(PickleParsingState):
    scalar_append_ops = [
        PklOp.BINUNICODE, PklOp.BININT, PklOp.BININT1, PklOp.BININT2,
    ]
        
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        op = ctx.current_op

        # Setup for next opcode before we handle current op.
        ctx._next_state(PickleParsingOpCode)
        #print('------------------------------------------')
        #pprint(ctx.stack)
        #print(op)
        #breakpoint()

        if op.opcode == PklOp.PROTO:
            if ctx.node().proto is not None:
                raise UnsupportedFormatException("PROTO defined twice in single stream?!")
            ctx.node().proto = op.param
            ctx.history.append(op)
            return

        if op.opcode == PklOp.EMPTY_DICT:
            ctx.stack.append({})
            ctx.history.append(op)
            return

        if op.opcode == PklOp.EMPTY_LIST:
            ctx.stack.append([])
            ctx.history.append(op)
            return

        if op.opcode == PklOp.EMPTY_SET:
            ctx.stack.append(set())
            ctx.history.append(op)
            return

        if op.opcode == PklOp.EMPTY_TUPLE:
            ctx.stack.append(tuple())
            ctx.history.append(op)
            return

        if op.opcode in [PklOp.BINPUT, PklOp.LONG_BINPUT]:
            ctx.memo[op.param] = ctx.stack[-1]
            ctx.history.append(op)
            return

        if op.opcode == PklOp.MARK:
            # Note: Not sure if we need to be more explicit.
            ctx.stack.append(StackMark(op))
            ctx.history.append(op)
            return

        if op.opcode in PickleInterpreter.scalar_append_ops:
            ctx.stack.append(op.param)
            ctx.history.append(op)
            return

        if op.opcode == PklOp.GLOBAL:
            ctx.stack.append((op.param, op.param2))
            ctx.history.append(op)
            return

        if op.opcode == PklOp.TUPLE:

            # Build Tuple
            value = tuple()
            entry = ctx.stack.pop()
            while not isinstance(entry, StackMark):
                value = (entry, *value)
                entry = ctx.stack.pop()
            
            # Remove StackMark and push tuple.
            ctx.stack.append(value)
            ctx.history.append(op)

            # TODO: Record instructions that involve tuple.
            return
            
        if op.opcode == PklOp.BINPERSID:
            arg = ctx.stack.pop()
            ctx.stack.append(PersistentCall(op.param, arg, op))
            ctx.history.append(op)
            return

        if op.opcode == PklOp.TUPLE3:
            if len(ctx.stack) < 3:
                breakpoint()
                raise Exception("Missing TUPLE3 arguments.")
            value = (ctx.stack.pop(), ctx.stack.pop(), ctx.stack.pop())
            ctx.stack.append(value)
            ctx.history.append(op)
            return

        if op.opcode == PklOp.TUPLE2:
            if len(ctx.stack) < 2:
                raise Exception("Missing TUPLE2 arguments.")
            value = (ctx.stack.pop(), ctx.stack.pop())
            ctx.stack.append(value)
            ctx.history.append(op)
            return

        if op.opcode == PklOp.TUPLE1:
            if len(ctx.stack) < 1:
                raise Exception("Missing TUPLE1 arguments.")
            value = tuple([ctx.stack.pop()])
            ctx.stack.append(value)
            ctx.history.append(op)
            return

        if op.opcode == PklOp.NEWFALSE:
            ctx.stack.append(False)
            ctx.history.append(op)
            return

        if op.opcode == PklOp.REDUCE:
            arg = ctx.stack.pop()
            module_call = ctx.stack.pop()
            ctx.stack.append(ReduceCall(module_call, arg, op))
            ctx.history.append(op)
            return
        
        if op.opcode in [PklOp.BINGET, PklOp.LONG_BINGET]:
            ctx.stack.append(ctx.memo[op.param])
            ctx.history.append(op)
            return

        if op.opcode == PklOp.SETITEMS:

            # Expect dict before mark.
            mark_index = None
            for i in range(len(ctx.stack) - 1, -1, -1):
                if isinstance(ctx.stack[i], StackMark):
                    mark_index = i
                    break
            if mark_index is None:
                raise Exception("Mark not found for SETITEMS")

            dict_obj = ctx.stack[mark_index - 1]

            while len(ctx.stack) > mark_index + 1:
                value = ctx.stack.pop()
                key = ctx.stack.pop()
                dict_obj[key] = value

            # Consume the MARK
            ctx.stack.pop()

            ctx.history.append(op)

            # TODO: Record instructions that involve tuple.
            return

        breakpoint()
        


        
            
            

        


        
        




        
                


class PickleParsingOpCode(PickleParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.read(1)
        if not data or len(data) < 1:
            raise pparse.EndOfDataException("Not enough data to parse pickle opcode")

        op = PklOp(data[0])
        ctx.current_op = op

        # Get the next opcode.
        if PklOp.no_params(data[0]):
            if op.opcode == PklOp.STOP:
                # End of the Pickle stream, pop it.
                ctx.node().value = ctx.stack
                parser._end_container_node(ctx)
                parser.current.ctx()._next_state(PickleParsingPickleStream)
                return
            # Do interpreter with new code.
            ctx._next_state(PickleInterpreter)
            return
        elif PklOp.is_simple(data[0]):
            ctx._next_state(PickleParsingSimpleParam)
            return
        elif PklOp.has_length(data[0]):
            ctx._next_state(PickleParsingLengthPrefix)
            return
        elif PklOp.is_readline(data[0]):
            ctx._next_state(PickleParsingReadlineParam)
            return
        else:
            raise UnsupportedFormatException(f"Invalid pickle opcode: {hex(data[0])}")
        
        


# State where we switch pickle streams, delimited by STOP.
class PickleParsingPickleStream(PickleParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(1)
        if not data or len(data) < 1:
            raise pparse.EndOfDataException("Not enough data to parse pickle opcode")

        parent = parser.current
        newpkl = NodePickle(parent, ctx.reader())
        newpkl.ctx()._next_state(PickleParsingOpCode)
        parent.value.append(newpkl)
        parser.current = newpkl
        trace("Starting new pkl stream.")



#!/usr/bin/env python3

import json

from thirdparty.pparse.lib import (
    EndOfDataException,
    UnsupportedFormatException,
    EndOfNodeException
)


class JsonParsingState(object):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        raise NotImplementedError()


class JsonParsingNumber(JsonParsingState):
    def __init__(self):
        self.num_bytes = []

    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(0x400)
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
        ctx.read(offset)

        if done:
            try:
                parser._apply_node_value(ctx, json.loads(b''.join(self.num_bytes)))
            except Exception as e:
                raise UnsupportedFormatException(f"Invalid number format in {self.num_bytes}: {e}")
            finally:
                self.num_bytes = []
            
        ctx._next_state(JsonParsingMeta)


class JsonParsingString(JsonParsingState):
    def __init__(self):
        self.str_bytes = [b'\x22']

    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(0x400)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse JSON string.")

        offset = 0
        while offset < len(data) and len(data) - offset >= 1:
            # if data.startswith(b'This is a synthetic') and offset == 218:
            #     breakpoint()
            if data[offset:offset+1] == b'\x22':
                # We're done
                try:
                    value = ctx.read(offset+1)
                    self.str_bytes.append(value)
                    encoded_string = json.loads(b''.join(self.str_bytes))
                    parser._apply_node_value(ctx, encoded_string)
                except Exception as e:
                    raise UnsupportedFormatException(f"Invalid string format in {self.str_bytes}: {e}")
                finally:
                    self.str_bytes = [b'"']
                
                ctx._next_state(JsonParsingMeta)
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
        
        value = ctx.read(offset)
        self.str_bytes.append(value)


class JsonParsingWhitespace(JsonParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(0x400)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON whitespace.")
        
        offset = 0
        while offset < len(data):
            if not data[offset:offset+1] in b'\x09\x0a\x0d\x20':
                break
            offset += 1
        ctx.skip(offset)

        ctx._next_state(JsonParsingMeta)


class JsonParsingConstant(JsonParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(5)
        if len(data) < 4:
            raise EndOfDataException("Not enough data to parse JSON encoding.")
        
        if data[:1] == b'\x66':
            if len(data) < 5:
                raise EndOfDataException("Not enough data to parse JSON false.")
            if data[1:5] == b'\x61\x6c\x73\x65':
                parser._apply_node_value(ctx, False)
                ctx.skip(5)
                ctx._next_state(JsonParsingMeta)
                return
        elif data[:1] == b'\x6e':
            if len(data) < 4:
                raise EndOfDataException("Not enough data to parse JSON null.")
            if data[1:4] == b'\x75\x6c\x6c':
                parser._apply_node_value(ctx, None)
                ctx.skip(4)
                ctx._next_state(JsonParsingMeta)
                return
        elif data[:1] == b'\x74':
            if len(data) < 4:
                raise EndOfDataException("Not enough data to parse JSON true.")
            if data[1:4] == b'\x72\x75\x65':
                parser._apply_node_value(ctx, True)
                ctx.skip(4)
                ctx._next_state(JsonParsingMeta)
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

    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(1)
        if len(data) < 1:
            raise EndOfDataException(f"Not enough data to parse JSON meta. Offset: {ctx.tell()}")

        if data[:1] in JsonParsingMeta.WHITESPACE_BYTES:
            ctx._next_state(JsonParsingWhitespace)
            return

        if data[:1] in JsonParsingMeta.CONSTANT_BYTES:
            # TODO: New node?
            ctx.mark_field_start()
            ctx._next_state(JsonParsingConstant)
            return

        if data[:1] in JsonParsingMeta.NUMBER_BYTES:
            # TODO: New node?
            ctx.mark_field_start()
            ctx._next_state(JsonParsingNumber)
            return

        if data[:1] == JsonParsingMeta.DOUBLE_QUOTE:
            ctx.mark_field_start()
            ctx.skip(1) 
            ctx._next_state(JsonParsingString)
            return

        if data[:1] in JsonParsingMeta.COLON_COMMA:
            ctx.skip(1)
            return
        
        # ----- structure stuff -----

        if data[:1] == JsonParsingMeta.LEFT_BRACKET:
            ctx.mark_field_start() # TODO: relevant?
            parser._start_array_node(ctx)
            return
        
        if data[:1] == JsonParsingMeta.LEFT_CURLY:
            ctx.mark_field_start() # TODO: relevant?
            parser._start_map_node(ctx)
            return

        if data[:1] in JsonParsingMeta.RIGHT_BRACKET_CURLY:
            ctx.mark_field_start() # TODO: relevant?
            ctx.skip(1)
            parser._end_container_node(ctx)
            return

        raise UnsupportedFormatException(f"Not a valid JSON meta character: {data[:1]}")


class JsonParsingStart(JsonParsingState):

    VALID_BYTES = b'\x09\x0a\x0d\x20\x22\x2d\x5b\x5d\x66\x6e\x74\x7b\x7d' \
        b'\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39'

    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(2)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON encoding.")
        if not data[:1] in JsonParsingStart.VALID_BYTES or data[1] == b'\x00':
            raise UnsupportedFormatException("Not a valid UTF-8 Encoded JSON")
        
        ctx._next_state(JsonParsingMeta)
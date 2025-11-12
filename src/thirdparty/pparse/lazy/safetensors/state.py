#!/usr/bin/env python3

import json

from thirdparty.pparse.lib import (
    EndOfDataException,
    UnsupportedFormatException,
    EndOfNodeException
)


class SafetensorsParsingState(object):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        raise NotImplementedError()


class SafetensorsParsingTensors(SafetensorsParsingState):

    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(0x400)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON whitespace")
        
        
            
        ctx._next_state(JsonParsingMeta)


class SafetensorsParsingHeader(SafetensorsParsingState):

    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(0x400)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON whitespace")
        
        
            
        ctx._next_state(SafetensorsParsingTensors)


class SafetensorsParsingLength(SafetensorsParsingState):

    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(8)
        if len(data) < 8:
            raise EndOfDataException("Not enough data to parse Safetensors Header Length")

        # TODO: Save this somewhere
        header_length = struct.unpack('<Q', data)[0]
        ctx.skip(8)
            
        ctx._next_state(SafetensorsParsingHeader)



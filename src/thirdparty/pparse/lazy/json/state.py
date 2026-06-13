#!/usr/bin/env python3

from __future__ import annotations

import json
import logging
from typing import List

import thirdparty.pparse.lib as pparse

log = logging.getLogger(__name__)

from thirdparty.pparse.lib import (
    EndOfDataException,
    UnsupportedFormatException,
)


class JsonParsingState(object):


    def parse_data(self, node: pparse.Node) -> int:
        raise NotImplementedError()


class JsonParsingComplete(JsonParsingState):


    def parse_data(self, node: pparse.Node) -> int:
        return pparse.ASCEND


class JsonParsingNumber(JsonParsingState):


    def __init__(self) -> None:
        self.num_bytes: List[bytes] = []


    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()
        data = ctx.peek(0x400)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON whitespace")

        log.debug(f"JsonParsingNumber({id(node):x}) off {ctx.tell()} data {data[:10]}")

        NUM_BYTES = b"\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x2d\x2b\x65\x45\x2e"

        offset = 0
        done = False
        while offset < len(data):
            if data[offset : offset + 1] not in NUM_BYTES:
                done = True
                break
            self.num_bytes.append(data[offset : offset + 1])
            offset += 1
        ctx.read(offset)

        if done:
            try:
                parser.apply_node_value(node, json.loads(b"".join(self.num_bytes)))
            except Exception as e:
                breakpoint()
                raise UnsupportedFormatException(
                    f"Invalid number format in {self.num_bytes}: {e}"
                )
            finally:
                self.num_bytes = []

        ctx._next_state(JsonParsingMeta)

        return pparse.AGAIN


class JsonParsingString(JsonParsingState):


    def __init__(self) -> None:
        self.str_bytes: List[bytes] = [b"\x22"]


    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()
        data = ctx.peek(0x400)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse JSON string.")

        log.debug(f"JsonParsingString({id(node):x}) off {ctx.tell()} data {data[:10]}")

        offset = 0
        while offset < len(data) and len(data) - offset >= 1:
            # if data.startswith(b'This is a synthetic') and offset == 218:
            #     breakpoint()
            if data[offset : offset + 1] == b"\x22":
                # We're done
                try:
                    value = ctx.read(offset + 1)
                    self.str_bytes.append(value)
                    encoded_string = json.loads(b"".join(self.str_bytes))
                    parser.apply_node_value(node, encoded_string)
                except Exception as e:
                    raise UnsupportedFormatException(
                        f"Invalid string format in {self.str_bytes}: {e}"
                    )
                finally:
                    self.str_bytes = [b'"']

                ctx._next_state(JsonParsingMeta)
                return pparse.AGAIN

            elif data[offset : offset + 1] == b"\x5c":
                if data[offset + 1 : offset + 2] == b"\x75":
                    if len(data) < 6:
                        raise EndOfDataException(
                            "Not enough bytes to parse JSON enicode char in string."
                        )
                    self.str_bytes.append(data[offset : offset + 6])
                    offset += 6
                    continue
                if data[offset + 1] in b"\x22\x5c\x2f\x62\x66\x6e\x72\x74":
                    self.str_bytes.append(data[offset : offset + 2])
                    offset += 2
                    continue

            else:
                offset += 1

        value = ctx.read(offset)
        self.str_bytes.append(value)

        return pparse.AGAIN


class JsonParsingWhitespace(JsonParsingState):


    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        #parser = ctx.parser()

        data = ctx.peek(0x400)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON whitespace.")

        log.debug(f"JsonParsingWhitespace({id(node):x}) off {ctx.tell()} data {data[:10]}")

        offset = 0
        while offset < len(data):
            if data[offset : offset + 1] not in b"\x09\x0a\x0d\x20":
                break
            offset += 1
        ctx.skip(offset)

        ctx._next_state(JsonParsingMeta)

        return pparse.AGAIN


class JsonParsingConstant(JsonParsingState):


    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        data = ctx.peek(5)
        if len(data) < 4:
            raise EndOfDataException("Not enough data to parse JSON encoding.")
        
        log.debug(f"JsonParsingConstant({id(node):x}) off {ctx.tell()} data {data}")

        if data[:1] == b"\x66":
            if len(data) < 5:
                raise EndOfDataException("Not enough data to parse JSON false.")
            if data[1:5] == b"\x61\x6c\x73\x65":
                parser.apply_node_value(node, False)
                ctx.skip(5)
                ctx._next_state(JsonParsingMeta)
                return pparse.AGAIN
        elif data[:1] == b"\x6e":
            if len(data) < 4:
                raise EndOfDataException("Not enough data to parse JSON null.")
            if data[1:4] == b"\x75\x6c\x6c":
                parser.apply_node_value(node, None)
                ctx.skip(4)
                ctx._next_state(JsonParsingMeta)
                return pparse.AGAIN
        elif data[:1] == b"\x74":
            if len(data) < 4:
                raise EndOfDataException("Not enough data to parse JSON true.")
            if data[1:4] == b"\x72\x75\x65":
                parser.apply_node_value(node, True)
                ctx.skip(4)
                ctx._next_state(JsonParsingMeta)
                return pparse.AGAIN

        raise UnsupportedFormatException("Not a valid JSON constant.")


class JsonParsingMeta(JsonParsingState):
    WHITESPACE_BYTES = b"\x09\x0a\x0d\x20"
    CONSTANT_BYTES = b"\x66\x6e\x74"
    NUMBER_BYTES = b"\x2d\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39"
    COLON_COMMA = b"\x3a\x2c"
    DOUBLE_QUOTE = b"\x22"
    LEFT_BRACKET = b"\x5b"
    LEFT_CURLY = b"\x7b"
    RIGHT_BRACKET_CURLY = b"\x5d\x7d"


    def parse_data(self, node: pparse.Node) -> int:

        ctx = node.ctx()
        parser = ctx.parser()

        data = ctx.peek(1)
        if len(data) < 1:
            # TODO: This only works if its the end of the stream.
            if ctx.json_top:
                ctx._next_state(JsonParsingComplete)
                return pparse.ASCEND
            raise EndOfDataException(
                f"Not enough data to parse JSON meta. Offset: {ctx.tell()}"
            )

        log.debug(f"JsonParsingMeta({id(node):x}) off {ctx.tell()} data {data}")

        if data[:1] in JsonParsingMeta.WHITESPACE_BYTES:
            log.debug("  Entering JsonParsingWhitespace")
            ctx._next_state(JsonParsingWhitespace)
            return pparse.AGAIN

        if data[:1] in JsonParsingMeta.CONSTANT_BYTES:
            ctx.mark_field_start()
            log.debug("  Entering JsonParsingConstant")
            ctx._next_state(JsonParsingConstant)
            return pparse.AGAIN

        if data[:1] in JsonParsingMeta.NUMBER_BYTES:
            ctx.mark_field_start()
            log.debug("  Entering JsonParsingNumber")
            ctx._next_state(JsonParsingNumber)
            return pparse.AGAIN

        if data[:1] == JsonParsingMeta.DOUBLE_QUOTE:
            ctx.mark_field_start()
            ctx.skip(1)
            log.debug("  Entering JsonParsingString")
            ctx._next_state(JsonParsingString)
            return pparse.AGAIN

        if data[:1] in JsonParsingMeta.COLON_COMMA:
            ctx.skip(1)
            return pparse.AGAIN

        # ----- structure stuff -----

        if data[:1] == JsonParsingMeta.LEFT_BRACKET:
            ctx.mark_field_start()  # TODO: relevant?

            ctx.skip(1)
            log.debug("  Creating array node")
            arr_node = parser.new_array_node(node)
            log.debug("  Array node entering JsonParsingMeta")
            arr_node.ctx()._next_state(JsonParsingMeta)
            parser.apply_node_value(node, arr_node)

            # Instruct Node to descend into array node.
            ctx._descendants.append(arr_node)

            return pparse.AGAIN

        if data[:1] == JsonParsingMeta.LEFT_CURLY:
            ctx.mark_field_start()  # TODO: relevant?

            # At this point we have:
            # - A UNLOADED map node
            # - A start position
            # - TODO: State
            # Therefore, the node should be able to load itself.
            # TODO: Have the node continue loading itself?
            ctx.skip(1)
            log.debug("  Creating map node")
            map_node = parser.new_map_node(node)
            log.debug("  Map node entering JsonParsingMeta")
            map_node.ctx()._next_state(JsonParsingMeta)
            parser.apply_node_value(node, map_node)

            # Instruct Node to descend into map node.
            ctx._descendants.append(map_node)

            return pparse.AGAIN

        if data[:1] in JsonParsingMeta.RIGHT_BRACKET_CURLY:
            ctx.mark_field_start()  # TODO: relevant?

            ctx.skip(1)
            parser._end_container_node(node)

            log.debug("  Ascending to parent node.")

            return pparse.ASCEND

        # TODO: This only works if its invalid JSON.
        if ctx.json_top:
            ctx._next_state(JsonParsingComplete)
            return pparse.ASCEND
        raise UnsupportedFormatException(f"Not a valid JSON meta character: {data[:1]}")


class JsonParsingStart(JsonParsingState):
    VALID_BYTES: bytes = (
        b"\x09\x0a\x0d\x20\x22\x2d\x5b\x5d\x66\x6e\x74\x7b\x7d"
        b"\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39"
    )


    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        #parser = ctx.parser()

        data = ctx.peek(2)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse JSON encoding.")
        if data[:1] not in JsonParsingStart.VALID_BYTES or data[1] == b"\x00":
            raise UnsupportedFormatException("Not a valid UTF-8 Encoded JSON")

        # Marking the top allows us to not throw EndOfDataException when we return
        # to this node in JsonParsingMeta. We can not use parent == None to check
        # for top because this data could be part of a larger tree.
        ctx.json_top = True
        
        # Enter JsonParsingMeta via JsonParsingWhitespace to lstrip()
        # Note: Ignoring whitespace after JSON string.
        ctx._next_state(JsonParsingMeta)
        return pparse.AGAIN

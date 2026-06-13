#!/usr/bin/env python3

from __future__ import annotations

import io
import logging
import struct
import zlib
from typing import Any

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.zip.meta import Zip


class ZipParsingState(object):
    def parse_data(self, node: pparse.Node) -> int:
        raise NotImplementedError()


class ZipParsingComplete(ZipParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        #ctx = node.ctx()
        #parser = ctx.parser()

        return pparse.ASCEND
        # TODO: Do we spin?
        # context._next_state(ZipParsingComplete)
        raise pparse.EndOfDataException("No more data to process in zip.")


class ZipParsingFinishDecompress(ZipParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        #breakpoint()
        ctx = node.ctx()
        parser = ctx.parser()
        parser._end_container_node(node)

        return pparse.ASCEND


# ! UNTESTED
class ZipParsingDataDescFooter(ZipParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        #parser = ctx.parser()

        data = ctx.peek(Zip.FOOTER_LEN)
        if len(data) < Zip.FOOTER_LEN:
            return pparse.EndOfDataException("Not enough data to parse data desc footer")

        desc = {}
        (desc["sig"], desc["crc32"], desc["comp_size"], desc["uncomp_size"]) = (
            struct.unpack("<IIII", data[:Zip.FOOTER_LEN])
        )
        meta = ctx.parent()._value

        if meta["crc32"] != 0 and meta["crc32"] != desc["crc32"]:
            return pparse.ASCEND

        ctx.skip(Zip.FOOTER_LEN)
        meta["zip_desc"] = desc
        # Since we moved the position, we update the parent before ASCEND.
        ctx.parent().ctx().seek(ctx.tell())
        return pparse.ASCEND


class ZipParsingContinueDecompress(ZipParsingState):
    def __init__(self) -> None:
        self.decompressor: Any = zlib.decompressobj(-zlib.MAX_WBITS)
        self._has_desc: bool = False

    def _found_desc(self, ctx: pparse.NodeContext) -> bool:
        return ctx.peek(4).find(Zip.DATA_DESC_SIG) != -1

    def _compare_crc32(self, given: int, data: bytes) -> bool:
        return zlib.crc32(data) & 0xFFFFFFFF == given

    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        data = ctx.peek(4)
        if not data or len(data) < 4:
            raise pparse.EndOfDataException("Not enough data to continue decompression")

        # TODO: This should be able to handle anything between 4-N bytes, but
        # TODO: we should consider how we will chunk out very large buffers.

        meta = ctx.parent()._value
        if node._value == pparse.UNLOADED_VALUE:
            node._value = io.BytesIO()
        buffer = node._value

        # TODO: Is this a MemoryView or copy?
        #breakpoint()
        data = ctx.peek(ctx.left())
        log.debug(f"Looking at {meta['fname']} data. Length: {len(data)}")
        (used, unused, eof) = self.decompress_data(node, data)
        log.debug(f"Decompress data results: used {used} unused {unused} eof {eof}")

        ctx.skip(used)
        if eof:
            if meta["compression"] == 8:
                dedata = self.decompressor.flush()
                buffer.write(dedata)
                # Update parent context with current context offset.
                parser._end_container_node(node)
                return pparse.ASCEND

            # flags & 0x08 == true means we explicitly have a data desc
            # it is possible for a data desc to show up without the flags too
            if self._has_desc or self._found_desc(ctx):
                parser._end_container_node(node)
                ctx._next_state(ZipParsingDataDescFooter)
                #ctx.parent().ctx()._next_state(ZipParsingDataDescFooter)
                log.debug(f"End Of File Compression via footer desc (length {node.length()})")
                return pparse.AGAIN
            else:
                breakpoint()
                parser._end_container_node(ctx)
                log.debug(f"End Of File Compression via EOF marker (length {node.length()})")
                return pparse.ASCEND

        return pparse.AGAIN

    def _decompress_data(self, node: pparse.Node, comp_data: bytes) -> tuple[int, int, bool]:
        #eof = False
        buffer = node._value
        dedata = self.decompressor.decompress(comp_data)
        buffer.write(dedata)
        unused = len(self.decompressor.unused_data)
        used = len(comp_data) - unused
        return (used, unused, self.decompressor.eof)

    def decompress_data(self, node: pparse.Node, compressed_data: bytes) -> tuple[int, int, bool]:
        ctx = node.ctx()
        meta = ctx.parent()._value
        buffer = node._value

        # Be pesimistic
        used = 0
        unused = len(compressed_data)

        if meta["flags"] & 0x08:
            self._has_desc = True

        if meta["compression"] == 0:
            if meta["fname"].endswith("/"):
                return (0, 0, True)

            if meta["uncomp_size"] != 0:
                whats_left = meta["uncomp_size"] - buffer.tell()
                if whats_left > 0:
                    if whats_left > len(compressed_data):
                        whats_left = len(compressed_data)
                    buffer.write(compressed_data[:whats_left])
                return (
                    whats_left,
                    len(compressed_data) - whats_left,
                    buffer.tell() == meta["uncomp_size"],
                )

            else:
                # Dumb search for DATA_DESC_SIG
                if len(compressed_data) - 3 < 1:
                    raise pparse.EndOfDataException(
                        "Not enough data for data copy with desc."
                    )
                desc_off = compressed_data.find(Zip.DATA_DESC_SIG)
                if desc_off <= -1:
                    # Not found, consume everything but last 3 bytes.
                    buffer.write(compressed_data[:-3])
                    return (len(compressed_data) - 3, 3, False)
                else:
                    # Verify the CRC32 to verify no collision.
                    # TODO: Make sure get_value() returns a MemoryView and not a copy.
                    eof = self._compare_crc32(meta["crc32"], buffer.getvalue())
                    if not eof:
                        desc_off += 4
                    buffer.write(compressed_data[:desc_off])
                    return (desc_off, len(compressed_data) - desc_off, eof)

        elif meta["compression"] == 8:
            if not self._has_desc and meta["uncomp_size"] == buffer.tell():
                return (meta["comp_size"], 0, True)
            return self._decompress_data(node, compressed_data)
        elif meta["compression"] == 12:
            raise Exception("BZIP2 Compression not currently supported.")
        elif meta["compression"] == 14:
            raise Exception("LZMA Compression not currently supported.")
        else:
            raise Exception(f"Compression not supported. {meta['compression']}")

        return (used, unused, False)


class ZipParsingStartDecompress(ZipParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        node._value["decomp_data"] = parser.new_data_node(node)
        node._value["decomp_data"].ctx()._next_state(ZipParsingContinueDecompress)
        # Let Node.load() drive
        node.ctx()._descendants.append(node._value["decomp_data"])

        # Once decompression is done, allow ZipParsingFinishDecompress to sync offset.
        ctx._next_state(ZipParsingFinishDecompress)
        
        msg = f"Done initializing new Node for decompression for: {node._value['fname']}"
        log.debug(msg)
        return pparse.AGAIN


class ZipParsingEntryExtra(ZipParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        #parser = ctx.parser()

        extra_len = node._value["extra_len"]
        data = ctx.peek(extra_len)
        if (extra_len != 0 and not data) or len(data) < extra_len:
            raise pparse.EndOfDataException("Not enough data to parse entry extra.")

        ctx.skip(extra_len)
        node._value["extra"] = data[:extra_len]

        log.debug(f"Done getting extra data for: {node._value['fname']}")

        # TODO: Determine if we generate node and defer the decompression or continue to decompress.
        ctx._next_state(ZipParsingStartDecompress)

        return pparse.AGAIN


class ZipParsingEntryFilename(ZipParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        #parser = ctx.parser()

        fname_len = node._value["fname_len"]
        data = ctx.peek(fname_len)
        if not data or len(data) < fname_len:
            raise pparse.EndOfDataException("Not enough data to parse file name")

        ctx.skip(fname_len)
        node._value["fname"] = data[:fname_len].decode("utf-8")

        log.debug(f"Done getting filename for new file: {node._value['fname']}")
        ctx._next_state(ZipParsingEntryExtra)
        return pparse.AGAIN


class ZipParsingEntryHeader(ZipParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        #parser = ctx.parser()

        data = ctx.peek(Zip.HEADER_LEN)
        if not data or len(data) < Zip.HEADER_LEN:
            raise pparse.EndOfDataException("Not enough data to parse zip entry header.")

        ctx.skip(Zip.HEADER_LEN)
        (
            node._value["version"],
            node._value["flags"],
            node._value["compression"],
            node._value["mod_time"],
            node._value["mod_date"],
            node._value["crc32"],
            node._value["comp_size"],
            node._value["uncomp_size"],
            node._value["fname_len"],
            node._value["extra_len"],
        ) = struct.unpack("<HHHHHIIIHH", data[:Zip.HEADER_LEN])

        log.debug("Done getting header for new file")
        ctx._next_state(ZipParsingEntryFilename)
        return pparse.AGAIN


class ZipParsingMagic(ZipParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        data = ctx.peek(4)
        if not data or len(data) < 4:
            raise pparse.EndOfDataException("Not enough data to detect zip magic")

        ctx.skip(4)
        if data[0:4] == Zip.DIR_SIG:
            # TODO: Try to parse it?
            ctx._next_state(ZipParsingComplete)
            return pparse.ASCEND

        if data[0:4] == Zip.LOCAL_FILE_HEADER:
            # TODO: Try to parse it?
            ctx._next_state(ZipParsingComplete)
            return pparse.ASCEND

        if data[0:4] == Zip.SIGNATURE:
            new_map = parser.new_map_node(node)
            new_map.ctx()._next_state(ZipParsingEntryHeader)
            node._value.append(new_map)
            # Let Node.load() drive.
            node.ctx()._descendants.append(new_map)
            # Note: this ctx state remains ZipParsingMagic 
            return pparse.AGAIN

        breakpoint()
        # pprint(parser.source()._result['zip'].value[0].value)
        raise pparse.UnsupportedFormatException(f"Invalid Zip Magic Bytes: {data}")

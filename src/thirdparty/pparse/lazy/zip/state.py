#!/usr/bin/env python3

import struct
import zlib
import io

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.zip.meta import Zip
from thirdparty.pparse.lazy.zip.node import Node, NodeMap, NodeArray



def trace(*args, **kwargs):
    print(*args, **kwargs)
    pass


class ZipParsingState(object):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        raise NotImplementedError()


class ZipParsingComplete(ZipParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        # TODO: Do we spin?
        #context._next_state(ZipParsingComplete)
        raise pparse.EndOfDataException("No more data to process in zip.")

    
class ZipParsingFinishDecompress(ZipParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        parser._end_container_node(ctx)
        # TODO: Not sure this is required.
        parser.current.ctx()._next_state(ZipParsingMagic)
        return


class ZipParsingDataDescFooter(ZipParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(Zip.FOOTER_LEN)
        if len(data) < Zip.FOOTER_LEN:
            return pparse.EndOfDataException("Not enough data to parse data desc footer")
        
        desc = {}
        (desc['sig'], desc['crc32'], desc['comp_size'], desc['uncomp_size']) \
            = struct.unpack("<IIII", data[:Zip.FOOTER_LEN])
        meta = ctx.node().value

        if meta['crc32'] != 0 and meta['crc32'] != desc['crc32']:
            ctx._next_state(ZipParsingFinishDecompress)
            return

        ctx.skip(Zip.FOOTER_LEN)
        meta['zip_desc'] = desc
        ctx._next_state(ZipParsingFinishDecompress)


class ZipParsingContinueDecompress(ZipParsingState):

    def __init__(self):
        self.decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
        self._has_desc = False

    def _found_desc(self, ctx):
        return ctx.peek(4).find(Zip.DATA_DESC_SIG) != -1

    def _compare_crc32(self, given, data):
        return zlib.crc32(data) & 0xFFFFFFFF == given

    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(4)
        if not data or len(data) < 4:
            raise pparse.EndOfDataException("Not enough data to continue decompression")
        
        # TODO: This should be able to handle anything between 4-N bytes, but
        # TODO: we should consider how we will chunk out very large buffers.

        meta = ctx.parent().value
        buffer = ctx.node().value
        # TODO: Is this a MemoryView or copy?
        data = ctx.peek(ctx.left())
        trace(f"Looking at {meta['fname']} data. Length: {len(data)}")
        (used, unused, eof) = self.decompress_data(ctx, data)
        trace(f"Decompress data results: used {used} unused {unused} eof {eof}")

        ctx.skip(used)
        if eof:
            if meta['compression'] == 8:
                dedata = self.decompressor.flush()
                buffer.write(dedata)

            # flags & 0x08 == true means we explicitly have a data desc
            # it is possible for a data desc to show up without the flags too
            if self._has_desc or self._found_desc(ctx):
                parser._end_container_node(ctx)
                ctx.parent_ctx()._next_state(ZipParsingDataDescFooter)
                trace(f"End Of File Compression via footer desc (length {ctx.node().length()})")
                return
            else:
                parser._end_container_node(ctx)
                ctx.parent_ctx()._next_state(ZipParsingFinishDecompress)
                trace(f"End Of File Compression via EOF marker (length {ctx.node().length()})")
                return

    def _decompress_data(self, ctx: 'NodeContext', comp_data):
        eof = False
        dedata = self.decompressor.decompress(comp_data)
        context.zip_entry.add_data(dedata)
        unused = len(self.decompressor.unused_data)
        used = len(comp_data) - unused
        return (used, unused, self.decompressor.eof)

    def decompress_data(self, ctx: 'NodeContext', compressed_data):
        meta = ctx.parent().value
        buffer = ctx.node().value
        # Be pesimistic
        used = 0
        unused = len(compressed_data)

        if meta['flags'] & 0x08:
            self._has_desc = True

        if meta['compression'] == 0:
            if meta['fname'].endswith('/'):
                return (0, 0, True)
            
            if meta['uncomp_size'] != 0:
                whats_left = meta['uncomp_size'] - buffer.tell()
                if whats_left > 0:
                    if whats_left > len(compressed_data):
                        whats_left = len(compressed_data)
                    buffer.write(compressed_data[:whats_left])
                return (whats_left, len(compresed_data)-whats_left, buffer.tell() == meta['uncomp_size'])
            
            else:
                # Dumb search for DATA_DESC_SIG
                if len(compressed_data) - 3 < 1:
                    raise pparse.EndOfDataException("Not enough data for data copy with desc.")
                desc_off = compressed_data.find(Zip.DATA_DESC_SIG)
                if desc_off <= -1:
                    # Not found, consume everything but last 3 bytes.
                    buffer.write(compressed_data[:-3])
                    return (len(compressed_data) - 3, 3, False)
                else:
                    # Verify the CRC32 to verify no collision.
                    # TODO: Make sure get_value() returns a MemoryView and not a copy.
                    eof = self._compare_crc32(meta['crc32'], buffer.getvalue())
                    if not eof:
                        desc_off += 4
                    buffer.write(compressed_data[:desc_off])
                    return (desc_off, len(compressed_data) - desc_off, eof)
        
        elif meta['compressed'] == 8:
            if not self._has_desc and meta['uncomp_size'] == buffer.tell():
                return (meta['comp_size'], 0, True)
            return self._decompress_data(context, compressed_data)
        else:
            raise Exception(f"Compression not supported. {meta['compression']}")

        return (used, unused, False)


class ZipParsingStartDecompress(ZipParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        # TODO: How do we determine if we want to skip? Should bias towards lazy.
        parent = parser.current
        newnode = Node(parent, ctx.reader())
        newnode.ctx()._next_state(ZipParsingContinueDecompress)
        # TODO: Being lazy atm moment, we should probably be able to
        #       write directly to an Extraction.
        newnode.value = io.BytesIO()
        ctx.node().value['decomp_data'] = newnode
        parser.current = newnode

        trace(f"Done initializing new Node for decompression for: {ctx.node().value['fname']}")


class ZipParsingEntryExtra(ZipParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        if not isinstance(ctx.node(), NodeMap):
            trace("Expected NodeMap parsing EntryFilename")
            breakpoint()

        meta = ctx.node().value
        extra_len = meta['extra_len']
        data = ctx.peek(extra_len)
        if not data or len(data) < extra_len:
            raise pparse.EndOfDataException("Not enough data to parse entry extra.")
        
        ctx.skip(extra_len)
        meta['extra'] = data[:extra_len]

        trace(f'Done getting extra data for: {meta['fname']}')
        ctx._next_state(ZipParsingStartDecompress)


class ZipParsingEntryFilename(ZipParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        if not isinstance(ctx.node(), NodeMap):
            trace("Expected NodeMap parsing EntryFilename")
            breakpoint()

        meta = ctx.node().value
        fname_len = meta['fname_len']
        data = ctx.peek(fname_len)
        if not data or len(data) < fname_len:
            raise pparse.EndOfDataException("Not enough data to parse file name")
        
        ctx.skip(fname_len)
        meta['fname'] = data[:fname_len].decode('utf-8')

        trace(f"Done getting filename for new file: {meta['fname']}")
        ctx._next_state(ZipParsingEntryExtra)


class ZipParsingEntryHeader(ZipParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        if not isinstance(ctx.node(), NodeMap):
            trace("Expected NodeMap parsing Header")
            breakpoint()

        data = ctx.peek(Zip.HEADER_LEN)
        if not data or len(data) < Zip.HEADER_LEN:
            raise pparse.EndOfDataException("Not enough data to parse zip entry header.")

        meta = ctx.node().value
        ctx.skip(Zip.HEADER_LEN)
        ( meta['version'], meta['flags'], meta['compression'], meta['mod_time'],
          meta['mod_date'], meta['crc32'], meta['comp_size'], meta['uncomp_size'],
          meta['fname_len'], meta['extra_len'],
        ) = struct.unpack('<HHHHHIIIHH', data[:Zip.HEADER_LEN])

        trace("Done getting header for new file")
        ctx._next_state(ZipParsingEntryFilename)


class ZipParsingMagic(ZipParsingState):
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        data = ctx.peek(4)
        if not data or len(data) < 4:
            raise pparse.EndOfDataException("Not enough data to detect zip magic")
        
        ctx.skip(4)
        if data[0:4] == Zip.DIR_SIG:
            ctx._next_state(ZipParsingComplete)
            return
        
        if data[0:4] == Zip.LOCAL_FILE_HEADER:
            ctx._next_state(ZipParsingComplete)
            return

        if data[0:4] == Zip.SIGNATURE:

            if not isinstance(parser.current, NodeArray):
                trace("Expected NodeArray")
                breakpoint()

            newmap = NodeMap(parser.current, ctx.reader())
            newmap.ctx()._next_state(ZipParsingEntryHeader)
            parser.current.value.append(newmap)
            parser.current = newmap
            return
        
        breakpoint()
        # pprint(parser.source()._result['zip'].value[0].value)
        raise pparse.UnsupportedFormatException(f"Invalid Zip Magic Bytes: {data}")




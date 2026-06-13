#!/usr/bin/env python3

from __future__ import annotations

import struct
import logging

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.om.meta import Partition

class OmParsingState(object):
    def parse_data(self, node: pparse.Node) -> int:
        raise NotImplementedError()


class OmParsingComplete(OmParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        return pparse.ASCEND


class OmParsingPartitionModelDef(OmParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        # Re-position ctx to actual protobuf data, based on some assumptions.
        FILE_HEADER_SIZE = 0x100
        MODELDEF_HEADER_SIZE= 0x80 #(OR partition table size? 5 * 24 + 8)
        ctx.seek(FILE_HEADER_SIZE + node._value['offset'] + MODELDEF_HEADER_SIZE)

        from thirdparty.pparse.lazy.protobuf import configure_pparser
        from thirdparty.pparse.lazy.protobuf.meta import PbImport

        # Define the range of data, based on partition table.
        pb_data = pparse.Range(ctx.dup(), node._value['size'] - MODELDEF_HEADER_SIZE)

        # Fetch protobuf schema.
        from importlib import resources
        data_path = resources.files("thirdparty.pparse.data")
        proto = PbImport(data_path / "proto" / "ge_ir.pb")

        # Setup the parser for descendant iteration.
        pb_parser_class = configure_pparser(ext_list=['.pb'], init_msgtype=".ge.proto.ModelDef", proto=proto)
        pb_parser = pb_parser_class.from_reader(pb_data, node)
        node._value['protobuf'] = pb_parser._root
        ctx._descendants.append(pb_parser._root)

        ctx._next_state(OmParsingComplete)
        return pparse.AGAIN


class OmParsingPartitionEntry(OmParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        data = ctx.peek(24)
        if len(data) < 24:
            raise pparse.EndOfDataException("Not enough data to parse partition table entry")

        #entry = parser._new_nodemap(parser.current, ctx.reader())
        edict = node._value
        edict['type'], edict['offset'], edict['size'] = struct.unpack('<QQQ', data[:24])

        #parser.current.value.append(entry)
        ctx.skip(24)

        # Set state of node based on type.
        # TODO: We'll likely have to always process ModelDef first, than to the others.
        if edict['type'] == Partition.MODELDEF:
            ctx._next_state(OmParsingPartitionModelDef)
        else:
            ctx._next_state(OmParsingComplete)
        return pparse.AGAIN

        # if parser.current.ctx().parent().value['partition_count'] > len(parser.current.value):
        #     ctx._next_state(OmParsingPartitionEntry)
        # else:
        #     ctx._next_state(OmParsingModelDef)


class OmParsingPartitionTable(OmParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        data = ctx.peek(8)
        if len(data) < 8:
            raise pparse.EndOfDataException("Not enough data to parse partition table count")

        partition_count = struct.unpack('<Q', data[:8])[0]
        node._value['partition_count'] = partition_count
        ctx.skip(8)

        # Create partition table.
        node._value['partition_table'] = parser.new_array_node(node)
        # Create all partition entries.
        for i in range(partition_count):
            partition = parser.new_map_node(node)
            partition.ctx()._next_state(OmParsingPartitionEntry)
            node._value['partition_table']._value.append(partition)
            ctx.skip(24)
        # Add to descendants for processing.
        for partition in node._value['partition_table']._value:
            ctx._descendants.append(partition)

        # ---- old stuff ----
        # #ctx.mark_field_start()
        # parent = parser.current
        # newarr = parser._new_nodearray(parent, ctx.reader())
        # parser.current.value['partitions'] = newarr
        # parser.current = parser.current.value['partitions']

        # if partition_count > 0:
        #     parser.current.ctx()._next_state(OmParsingPartitionEntry)
        # else:
        #     parser.current.ctx()._next_state(OmParsingComplete)
        node._value['partition_table'].ctx()._next_state(OmParsingComplete)
        ctx._next_state(OmParsingComplete)
        return pparse.ASCEND


class OmParsingHeader(OmParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        data = ctx.peek(0x100)
        if len(data) < 0x100:
            raise pparse.EndOfDataException("Not enough data to parse om header")

        node._value['file_header'] = data
        ctx.skip(0x100)
        ctx._next_state(OmParsingPartitionTable)
        return pparse.AGAIN

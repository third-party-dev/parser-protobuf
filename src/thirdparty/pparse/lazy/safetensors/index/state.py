#!/usr/bin/env python3

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse


class SafetensorsIndexParsingState(object):


    def parse_data(self, node: pparse.Node) -> int:
        raise NotImplementedError()


class SafetensorsIndexParsingComplete(SafetensorsIndexParsingState):


    def parse_data(self, node: pparse.Node) -> int:
        return pparse.ASCEND


class SafetensorsIndexParsingTensors(SafetensorsIndexParsingState):


    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        # parser = ctx.parser()

        node._value['tensors'] = {}
        for stfname in node._value['stfiles']:
            tensors = node._value['stfiles'][stfname].value['header'].value.value
            tensor_data = node._value['stfiles'][stfname]._value['tensors']
            for tname in tensors:
                if tname == "__metadata__":
                    continue
                node._value['tensors'][tname] = {}
                node._value['tensors'][tname]['header'] = tensors[tname]
                node._value['tensors'][tname]['data'] = tensor_data[tname]

        ctx._next_state(SafetensorsIndexParsingComplete)
        return pparse.ASCEND


class SafetensorsIndexParsingShards(SafetensorsIndexParsingState):


    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        # parser = ctx.parser()

        from thirdparty.pparse.lazy.safetensors import configure_pparser

        # ! Super hacky way to get path to the weight_map files.
        from pathlib import Path

        prefix = Path(node._reader._cursor._data._path).parent

        weight_map = node.value['index'].value.value['weight_map'].value
        for tname in weight_map:
            st_fpath = str(prefix / weight_map[tname])
            st_parser = configure_pparser().from_fpath(st_fpath)

            node._value.setdefault('stfiles', {})[st_fpath] = st_parser.make_root_node(parent=node)
            ctx._descendants.append(node._value['stfiles'][st_fpath])

        ctx._next_state(SafetensorsIndexParsingTensors)
        return pparse.AGAIN


class SafetensorsIndexParsingIndex(SafetensorsIndexParsingState):


    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        # parser = ctx.parser()

        from thirdparty.pparse.lazy.json import configure_pparser

        json_parser = configure_pparser().from_reader(node.ctx().reader())

        node._value['index'] = json_parser.make_root_node(parent=node)
        node.ctx()._descendants.append(node._value['index'])

        ctx._next_state(SafetensorsIndexParsingShards)

        return pparse.AGAIN

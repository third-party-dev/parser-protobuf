#!/usr/bin/env python3

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse

class PyTorchParsingState(object):
    def parse_data(self, node: pparse.Node) -> int:
        raise NotImplementedError()


class PyTorchParsingComplete(PyTorchParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        breakpoint()
        return pparse.ASCEND


class PyTorchParsingTensorsMeta(PyTorchParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        parser = ctx.parser()

        # TODO: Detect if Node.load(recursive=True)?

        # TODO: Using the metadata from pickle, generate nodes for tensors.

        # We only need the data reference, we seek(tensor_data_start) for each node.
        #tensor_reader = ctx.reader()
        node._value['tensors'] = {}

        # Auto-detect if this is a weights only model or not.
        pkl = node._value['pkl']._value[0]._value[0]

        # node._value - root pytorch node
        # node._value['pkl']._value - root pickle node (list).
        # node._value['pkl']._value[0] - First pickle stream.
        # node._value['pkl']._value[0].ctx() - NodeVmContext.
        # node._value['pkl']._value[0]._value - Pickle stream's stack (list).
        # node._value['pkl']._value[0]._value[0] - REDUCE_CALL on stack.

        if type(pkl).__name__ != 'ReduceCall' and type(pkl).__name__ != 'NewCall':
            # TODO: pkl start is assumed at a specific path. Need to allow specifying path.
            raise pparse.UnsupportedFormatException(f"Expected ReduceCall in pickle, found {type(pkl).__name__}.")

        # TODO: Consider adding option to "force_traversal".
        if len(pkl) == 0:
            #arr = []
            parser._traverse_pt(node, pkl.state)
        else:
            for name in pkl:
                #node._value['tensors'][name] = Tensor(node, pkl[name], name)

                # ! There is a bug here when processing yolov5su.

                tensor = parser.get_tensor_node(node, name, pkl[name])
                # ! TODO: Check if the name has already been set!
                node._value['tensors'][name] = tensor

        # We're done.
        ctx._next_state(PyTorchParsingComplete)
        return pparse.ASCEND


class PyTorchParsingPickle(PyTorchParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        #parser = ctx.parser()

        data_pkl_obj = None
        for fname in node._value['by_fname']:
            if fname.endswith('data.pkl'):
                data_pkl_obj = node._value['by_fname'][fname]
                break
        if not data_pkl_obj:
            raise pparse.UnsupportedFormatException("No data.pkl in pytorch zip.")

        from thirdparty.pparse.lazy.pickle import configure_pparser
        bytes_io = data_pkl_obj._value['decomp_data']._value
        pkl_parser = configure_pparser().from_bytesio(bytes_io)
        node._value['pkl'] = pkl_parser.make_root_node(parent=node)
        ctx._descendants.append(node._value['pkl'])

        # ! Assuming success. TODO: Node should be able to verify pkl parse success before continuing.
        ctx._next_state(PyTorchParsingTensorsMeta)
        return pparse.AGAIN


class PyTorchParsingZipPostProcess(PyTorchParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        #parser = ctx.parser()

        node._value['by_fname'] = {}
        for elem in node._value['zip']._value:
            node._value['by_fname'][elem._value['fname']] = elem

        ctx._next_state(PyTorchParsingPickle)
        return pparse.AGAIN


class PyTorchParsingZip(PyTorchParsingState):
    def parse_data(self, node: pparse.Node) -> int:
        ctx = node.ctx()
        #parser = ctx.parser()

        from thirdparty.pparse.lazy.zip import configure_pparser
        zip_parser = configure_pparser().from_reader(node.ctx().reader())
        node._value['zip'] = zip_parser.make_root_node(parent=node)
        ctx._descendants.append(node._value['zip'])

        # ! Assuming success. TODO: Node should be able to verify zip parse success before continuing.
        ctx._next_state(PyTorchParsingZipPostProcess)
        return pparse.AGAIN

        

from __future__ import annotations

import logging
from typing import Any, Iterator, Optional, Type

log = logging.getLogger(__name__)

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.pytorch.state import PyTorchParsingZip, PyTorchParsingState
from thirdparty.pparse.lazy.pytorch.meta import PT


def iter_new_calls(value: Any) -> Iterator[Any]:
    """Recursively yield every NewCall in the pickle value tree."""
    from thirdparty.pparse.lazy.pickle.calls import NewCall, ReduceCall, PersistentCall

    if isinstance(value, NewCall):
        yield value
        yield from iter_new_calls(value.arg)
        if value.state is not None:
            yield from iter_new_calls(value.state)
        yield from iter_new_calls(dict(value))
    elif isinstance(value, ReduceCall):
        yield from iter_new_calls(value.arg)
        if value.state is not None:
            yield from iter_new_calls(value.state)
        yield from iter_new_calls(dict(value))
    elif isinstance(value, PersistentCall):
        yield from iter_new_calls(value.arg)
    elif isinstance(value, dict):
        for v in value.values():
            yield from iter_new_calls(v)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from iter_new_calls(item)


def configure_pparser(**kwargs: Any) -> Type[pparse.Parser]:

    class Parser(pparse.Parser):


        @staticmethod
        def match_extension(fname: str) -> bool:
            if not fname:
                return False
            for ext in [".pt"]:
                if fname.endswith(ext):
                    return True
            return False


        @staticmethod
        def match_magic(cursor: pparse.Cursor) -> bool:
            # TODO: Is it a zip file?
            # TODO: Consider looking for data.pkl
            return False


        def make_root_node(
            self, parent: Optional[pparse.Node] = None, init_state: Type[PyTorchParsingState] = PyTorchParsingZip
        ) -> pparse.Node:
            init_state = self._init_state_as_cls(init_state)

            # Current path of pending things.
            root = pparse.Node(self._source.open(), self, default_value={}, parent=parent)
            root.ctx()._next_state(init_state)
            return root


        def __init__(self, source: pparse.Extraction, id: str = "pt") -> None:
            super().__init__(source, id, PyTorchParsingState)


        def _traverse_pt(
            self, node: pparse.Node, state: Any, path_arr: list[str] = [], metrics: dict[str, int] = {'param_cnt': 0}
        ) -> None:
            if not isinstance(state, dict) or not ('_modules' in state or '_parameters' in state):
                # print(f"  - Dead end.")
                return

            if '_parameters' in state and len(state['_parameters'].keys()) > 0:
                metrics['param_cnt'] += len(state['_parameters'].keys())
                for k in state['_parameters'].keys():
                    param_name = f"{'.'.join(path_arr)}.{k}"
                    # ! Being presumptuous on our part.

                    reduce_call = state['_parameters'][k].arg[2]

                    tensor = self.get_tensor_node(node, param_name, reduce_call)
                    # ! TODO: Check if the parameter name has already been set!
                    node._value['tensors'][param_name] = tensor

            if '_modules':
                for mod in state['_modules']:
                    self._traverse_pt(node, state['_modules'][mod].state, [*path_arr, mod], metrics)


        def get_pytorch_type(self, tensor_node: pparse.Node) -> str:
            persid = tensor_node._value['reduce_call'].arg[PT.PERSID_CALL]
            parts = [p.decode("utf-8").strip() for p in persid.arg[PT.TYPE_NAME]]
            return ".".join(parts)

            # type_tag = persid.arg[Tensor.TYPE_TAG]
            # type_name = persid.arg[Tensor.TYPE_NAME]
            # # torch.FloatStorage => dtype=float32
            # data_key = persid.arg[Tensor.DATA_KEY]
            # data_dest = persid.arg[Tensor.DATA_DEST]
            # elem_cnt = persid.arg[Tensor.ELEM_CNT]


        def get_type(self, tensor_node: pparse.Node) -> str:
            return PT.PKL_STTYPE_MAP[self.get_pytorch_type(tensor_node)]


        def get_shape(self, tensor_node: pparse.Node) -> list[int]:
            shape = [i for i in tensor_node._value['reduce_call'].arg[2]]
            shape.reverse()
            return shape


        # Return raw data as extracted from source
        def get_data_key(self, tensor_node: pparse.Node) -> str:
            persid = tensor_node._value['reduce_call'].arg[PT.PERSID_CALL]
            type_tag = persid.arg[PT.TYPE_TAG]
            if type_tag != "storage":
                raise Exception("Unexpected TYPE_TAG format when fetching tensor bytes.")
            return persid.arg[PT.DATA_KEY]


        def get_elem_count(self, tensor_node: pparse.Node) -> int:
            persid = tensor_node._value['reduce_call'].arg[PT.PERSID_CALL]
            type_tag = persid.arg[PT.TYPE_TAG]
            if type_tag != "storage":
                raise Exception("Unexpected TYPE_TAG format when fetching tensor bytes.")
            return persid.arg[PT.ELEM_CNT]


        def get_tensor_node(self, node: pparse.Node, name: str, reduce_call: Any) -> pparse.Node:
            ctx = node.ctx()
            tensor = pparse.Node(ctx.reader(), self, default_value={}, parent=node)
            tensor._value['reduce_call'] = reduce_call
            tensor._value['name'] = name
            tensor._value['type'] = self.get_type(tensor)
            tensor._value['shape'] = self.get_shape(tensor)
            tensor._value['elem_count'] = self.get_elem_count(tensor)
            tensor._value['data_key'] = self.get_data_key(tensor)

            # Create UNLOADED node with PyTorchParsingTensorNode state.
            decomp_data_obj = None
            for fname in node._value['by_fname']:
                if fname.endswith(f"data/{tensor._value['data_key']}"):
                    decomp_data_obj = node._value['by_fname'][fname]
                    break
            if not decomp_data_obj:
                raise pparse.UnsupportedFormatException(f"No data found for data_key {tensor._value['data_key']}")

            # Since we can use the Zip decomp_data's BytesIO object, its sufficient to point
            # our 'data' field at that Node.
            tensor._value['data'] = decomp_data_obj._value['decomp_data']
            return tensor

            # Note: Numpy Array and Python Array conversion isn't really "parsing", its more shaping
            #       and handling, therefore should be handled by the view class.

            # bytesio_obj = decomp_data_obj._value['decomp_data']._value
            # data_source = pparse.BytesIoData(bytes_io=bytesio_obj)
            # decomp_data_reader = pparse.Range(data_source.open(), data_source.length)
            # #tensor['data'] = pparse.Node(decomp_data_reader, parser, parent=tensor)
            # #tensor['data'].ctx()._next_state(PyTorchParsingTensorNode)

    return Parser

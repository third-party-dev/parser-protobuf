#!/usr/bin/env python3

import struct

import thirdparty.pparse.lib as pparse
from thirdparty.pparse.lazy.pickle.meta import PklOp
from thirdparty.pparse.lazy.pickle.vmnodes import NodeVmState


def trace(*args, **kwargs):
    print(*args, **kwargs)
    pass


class PklObjParsingState():
    def parse_data(self, parser: 'Parser', ctx: 'NodeContext'):
        raise NotImplementedError()
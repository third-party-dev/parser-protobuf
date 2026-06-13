#!/usr/bin/env python3

import logging

log = logging.getLogger(__name__)


class Zip:
    SIGNATURE: bytes = b"PK\x03\x04"
    DIR_SIG: bytes = b"PK\x05\x06"
    DATA_DESC_SIG: bytes = b"PK\x07\x08"
    LOCAL_FILE_HEADER: bytes = b"PK\x01\x02"

    HEADER_LEN: int = 26
    FOOTER_LEN: int = 16

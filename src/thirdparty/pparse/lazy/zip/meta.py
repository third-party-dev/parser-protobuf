#!/usr/bin/env python3

class Zip():
    SIGNATURE = b'PK\x03\x04'
    DIR_SIG = b'PK\x05\x06'
    DATA_DESC_SIG = b'PK\x07\x08'
    LOCAL_FILE_HEADER = b'PK\x01\x02'

    HEADER_LEN = 26
    FOOTER_LEN = 16
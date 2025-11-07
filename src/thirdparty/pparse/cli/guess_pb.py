








def is_utf8(data: bytes) -> bool:
    try:
        data.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False




def looks_like_submessage(data: bytes) -> bool:
    i = 0
    length = len(data)
    while i < length:
        # Try to parse a varint key
        key = 0
        shift = 0
        start = i
        while i < length:
            b = data[i]
            key |= (b & 0x7F) << shift
            i += 1
            if not (b & 0x80):
                break
            shift += 7
        else:
            return False  # incomplete varint

        field_number = key >> 3
        wire_type = key & 0x7

        if field_number == 0 or wire_type > 5:
            return False  # invalid protobuf key

        # Skip value based on wire_type
        if wire_type == 0:  # varint
            while i < length and (data[i] & 0x80):
                i += 1
            i += 1
        elif wire_type == 1:  # 64-bit
            i += 8
        elif wire_type == 2:  # length-delimited
            # parse varint length
            l = 0
            shift = 0
            while i < length:
                b = data[i]
                l |= (b & 0x7F) << shift
                i += 1
                if not (b & 0x80):
                    break
                shift += 7
            i += l
        elif wire_type == 5:  # 32-bit
            i += 4
        else:
            return False  # unknown wire type
    return True




def looks_like_packed_varints(data: bytes) -> bool:
    i = 0
    try:
        while i < len(data):
            # try reading a varint
            shift = 0
            while True:
                b = data[i]
                i += 1
                if not (b & 0x80):
                    break
                shift += 7
        return True
    except IndexError:
        return False



def classify_length_delimited(data: bytes) -> str:
    if is_utf8(data):
        return "string"
    elif looks_like_submessage(data):
        return "submessage"
    elif looks_like_packed_varints(data):
        return "packed_varint"
    elif len(data) % 4 == 0:
        return "packed_32bit"
    elif len(data) % 8 == 0:
        return "packed_64bit"
    else:
        return "bytes"



# Suppose you have a length-delimited field
data = b'\x08\x96\x01'  # example protobuf-encoded bytes

field_type = classify_length_delimited(data)
print(field_type)  # could print: "submessage" or "bytes"

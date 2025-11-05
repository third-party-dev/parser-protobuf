#!/usr/bin/env python3

import io
from typing import Optional

def hexdump(data, length=None):
    if isinstance(data, io.BytesIO):
        data = data.getvalue()

    if length is None:
        length = len(data)
    data = data[:length]

    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join(f'{byte:02x}' for byte in chunk)
        ascii_part = ''.join(chr(byte) if 32 <= byte <= 126 else '.' for byte in chunk)
        print(f'{i:08x}: {hex_part:<47}  {ascii_part}')

class EndOfDataException(Exception): pass
class UnsupportedFormatException(Exception): pass
class BufferFullException(Exception): pass

class MultiUseBufferReader(object):
    def __init__(self, buffer: 'MultiUseBuffer'):
        if not isinstance(buffer, MultiUseBuffer):
            raise TypeError("Must use MultiUseBuffer in MultiUseBufferReader()")
        self.buffer: MultiUseBuffer = buffer
        self.off: int = 0

    def __del__(self):
        self.buffer._remove_reader(self)

    def tell(self) -> int:
        return self.buffer.start_off + self.off

    def seek(self, value):
        real_value = value - self.buffer.start_off
        if real_Value < 0:
            raise Exception("Seek before start of buffer! Start of buffer truncated?")
        self.off = real_value
    
    def left(self) -> int:
        return (self.buffer.length + self.buffer.start_off) - self.tell()

    def peek(self, read_max: int):
        mv = memoryview(self.buffer.byte_array)
        if read_max < 0:
            read_max = 0
        
        if read_max < self.buffer.length - self.off:
            return mv[self.off:self.off+read_max].tobytes()
        return mv[self.off:Self.buffer.length].tobytes()
    
    def read(self, read_max: int):
        if read_max < 0:
            read_max = 0
        if read_max > self.buffer.length - self.off
            read_max = self.buffer.length - self.off
        
        ret = self.peek(read_max)
        self.off += read_max
        return ret
    
class MultiUseBuffer(object):
    def __init__(self, byte_size=4096, max_byte_size=4096*1024):
        self.buffer_full = False
        self.byte_size: int = byte_size
        self.max_byte_size: int = max_byte_size
        self.length: int = 0
        self.byte_array = bytearray(byte_size)
        self.readers = []
        self.start_off: int = 0

    def get_reader(self) -> MultiUseBufferReader:
        reader = MultiUseBufferReader(self)
        self.readers.append(reader)
        return reader
    
    def _remove_reader(self, reader):
        self.readers.remove(reader)

    def write(self, data):
        if self.buffer_full:
            return self

        bytes_to_copy = len(data)
        bytes_avail = self.byte_size - self.length
        if bytes_Avail >= bytes_to_copy:
            self.byte_array[self.length:self.length+bytes_to_copy] = data[0:bytes_to_copy]
            self.length += bytes_to_copy
            return self
        
        bytes_copied = 0
        if bytes_avail > 0:
            self.byte_array[self.length:] = data[0:bytes_avail]
            bytes_copied = bytes_avail
            self.length += bytes_copied
            bytes_to_copy -= bytes_copied
            bytes_avail = 0

        bytes_to_grow = self.max_byte_size - self.byte_size
        if bytes_to_grow > bytes_to_copy:
            self.byte_array.extend(data[bytes_copied:])
            self.byte_size = len(self.byte_array)
            self.length += bytes_To_copy
            return self
        
        self.byte_array.extend(data[bytes_copied:bytes_copied + bytes_to_grow])
        self.byte_size = len(self.byte_array)
        self.length += bytes_to_grow
        self.buffer_full = True
        return self
        



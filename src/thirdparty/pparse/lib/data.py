from __future__ import annotations

import io
import os
import stat
from typing import Any, Optional

from .reader import (
    Reader,
    Cursor,
)

# Data Considerations:
# - DiskData exists in its entirety on disk (even if truncated).
# - TapeData is constantly incoming and recorded (yes to Random Access).
#   - Need to re-mmap when data is appended.
# - StreamData is constantly incoming and only seen once (no to Random Access).

# StreamData may require entire stream to exist in memory, depending on parser
# references. A StreamData buffer can only deallocate data when all parsers
# have indicated they have no more need for the data range.


# Data interface.
class Data:
    def open(self, offset: int = 0) -> Cursor:
        return Cursor(self, offset)

    def peek(self, cursor: Cursor, length: int) -> bytes:
        raise NotImplementedError()

    def seek(self, cursor: Cursor) -> int:
        return cursor.tell()

    def read(self, cursor: Cursor, length: int) -> bytes:
        # Dumb implementation.
        data = self.peek(cursor, length)
        self.seek(cursor)
        return data


'''
  HttpRangedData is very dumb and slow. If we add caching, we can potentially bump the performance
  by more than double. The below metrics are misleading when comparing against each other. You need
  to understand the relationship between Range supported/not-supported, between deque based cache and
  linked list based cache, and the relationship between the application and the target kernels' page
  cache, and finally the fact that I tested all of these on the same system across the local network.

  Takeaways:
    - None of these tests include normal network latency.
    - All of the data from these tests lived in kernels page cache.
    - There were no other users on the system this was tested on.
    - FileData is a bit slower because it keeps file on disk, where HttpCacheData pulls
      most of the relevant data into memory. We could probably cache FileData in a similar
      way for a bit of speedup, especially in non-Linux environments (e.g. Windows).
    - The only meaningful numbers to compare are the Range supported cases where the
      whole file could not fit into memory at once. This shows that we've halved HttpRangedData
      behavior when using a cache.
    - Different formats jump around more so they'll produce different results. To mitigate this,
      there is a deliberate grab of chunks around the request for efficiency. This is similar to
      a CPU "read ahead" behavior (except with include "read behind" too.)

  Test results against `yolov5su_float32.tflite` (36832425 bytes / ~36MB)

    --- Control ---

    FileData with local file IO:
      real    0m0.714s
      user    0m1.006s
      sys     0m2.591s

    --- Naive Implementation ---

    HttpRangedData with Range header (i.e. test-server.py):
      real    0m15.338s
      user    0m9.357s
      sys     0m3.129s

    HttpRangedData without Range header (i.e. python -m http.server):
      * Not tested. (VERY LONG)

   --- Cached _without_ Range ---

    HttpCachedData with chunk_size 4096*1024, chunks 256, without Range header (i.e. python -m http.server):
      Note: 1,073,741,824B / 1GB cache using deque
      Note: Test case only valid when entire target fits in memory.

      real  0m0.573s
      user  0m0.951s
      sys   0m2.645s


    HttpCachedData with chunk_size 4096*256, chunks 1024, without Range header (i.e. python -m http.server):
      Note: 1,073,741,824B / 1GB cache using linked list
      Note: Test case only valid when entire target fits in memory.

      real  0m0.574s
      user  0m0.953s
      sys   0m2.421s


    HttpCachedData with chunk_size 4096, chunks 1024*256, without Range header (i.e. python -m http.server):
      Note: 1,073,741,824B / 1GB cache using linked list
      Note: Test case only valid when entire target fits in memory.
      Note: Bumped chunk count to see if there was a noticeable difference.

      real  0m0.616s
      user  0m1.003s
      sys   0m2.651s

    --- Cached _with_ Range ---

    HttpCachedData with chunk_size 4096, chunks 256, supported Range header (i.e. test-server.py):
      Note: 1,048,576B / 1MB cache using deque

      real  0m8.478s
      user  0m5.617s
      sys   0m2.892s


    HttpCachedData with chunk_size 256, chunks 4096, supported Range header (i.e. test-server.py):
      Note: 1,048,576B / 1MB cache using linked list

      real  0m8.478s
      user  0m5.617s
      sys   0m2.892s


    HttpCachedData with chunk_size 4096*1024, chunks 256, supported Range header (i.e. test-server.py):
      Note: 1,073,741,824B / 1GB cache using deque

      real  0m0.759s
      user  0m1.124s
      sys   0m2.502s


    HttpCachedData with chunk_size 4096*256, chunks 1024, supported Range header (i.e. test-server.py):
      Note: 1,073,741,824B / 1GB cache using linked list

      real  0m0.825s
      user  0m1.200s
      sys   0m2.620s

  Note: AWS has a minimal billable request size of 4K (i.e. 1 byte request is worth 4K in cash.)
'''

from thirdparty.pparse._httpdata import _HttpCachedData

class HttpCachedData(Data):
    # ~ 4MiB
    CHUNK_SIZE = 4096*256
    # Max Chunks
    MAX_CHUNKS = 1024

    def __init__(self, url: str, chunk_size: int = CHUNK_SIZE, chunk_max_count: int = MAX_CHUNKS, session: Optional[Any] = None) -> None:

        # ** If we're in a situation where we're requesting a file from a    **
        # ** remote resource that does not support Range, we might as well   **
        # ** download the whole thing and operate on it as a file. Any       **
        # ** realistic situation where the file is too big for memory, we'll **
        # ** not want to continually download the file when we don't have    **
        # ** the space we need in cache!                                     **

        # Detect the above scenario by fetching length and first chunk.
        self._session = session or requests.Session()
        response = self._session.head(url)
        response.raise_for_status()
        self.length = int(response.headers["Content-Length"])
        self._supports_ranges = response.headers.get("Accept-Ranges", "none").lower() == "bytes"

        if not self._supports_ranges and self.length > chunk_size * chunk_max_count:
            raise Exception("CAUTION: No ranged queries on server and target to large for cache.")

        self.httpdata = _HttpCachedData(url, chunk_size=chunk_size, chunk_max_count=chunk_max_count, session=self._session)


    # Read data ahead without progressing cursor.
    def peek(self, cursor: Cursor, length: int) -> bytes:
        return self.httpdata._read(cursor.tell(), length)



class HttpRangeData(Data):
    def __init__(self, url: Optional[str] = None) -> None:
        if not url:
            raise ValueError("url must be a string that points to a valid url")
        self._url = url
        self._session = requests.Session()
        #self._session.verify = "/path/to/ca-bundle.crt"
        #self._session.verify = False
        #self._session.cert = ("/path/to/client.crt", "/path/to/client.key")
        #self._session.headers["Authorization"] = "Bearer <token>"

        self.length = self._load_length()


    def _load_length(self) -> int:
        response = self._session.head(self._url)
        # TODO: Determine how to handle exceptions.
        response.raise_for_status()

        content_length = response.headers.get("Content-Length")
        if content_length is None:
            raise ValueError("Server did not return a Content-Length header.")

        return int(content_length)

    # Read data ahead without progressing cursor.
    def peek(self, cursor: Cursor, length: int) -> bytes:
        if length <= 0:
            return b""

        start = cursor.tell()
        end = start + length - 1
        headers = {"Range": f"bytes={start}-{end}"}

        response = self._session.get(self._url, headers=headers)
        response.raise_for_status()

        if response.status_code == 206:
            return response.content

        if response.status_code == 200:
            # TODO: Cache our content.
            # ! Being dumb and throwing away content.
            return response.content[start:start+length]
        raise IOError(f"Range request failed with status {response.status_code}")

    # Progress cursor without reading (no copy).
    def seek(self, cursor: Cursor) -> int:
        return cursor.tell()

    # Read the data.
    def read(self, cursor: Cursor, length: int) -> bytes:
        return self.peek(cursor, length)


'''
  TODO: Consider an architecture that allows stacking Data objects?
  Encodings: Utf8Data, Utf16Data, GzipData

  Utf8Data/Utf16Data should take a FileData or ByteIoData. Because
  Utf8 is not byte for byte, seeking is a challenge. A seek in utf8
  is based on glyphs whereas a seek on FileData is based on byte offset.

  To seek forward, we must read the FileData and periodically align
  Utf8 offset to byte offset. This will allow seeking backward to a
  sort of "keyframe" and then going forward to the exact offset.

  Performing the tracking of the keyframes depends on the available
  memory:
              1,048,576 -   1 MiB - @ 4MB =>
              4,194,304 -   4 MiB -
          1,073,741,824 -   1 GiB -
        549,755,813,888 - 512 GiB -
    281,474,976,710,656 - 256 TiB - @ 4MB => 536,870,912 (512MiB)

  To enable parsing of large file sizes, a tree can be used with larger keyframes and then a cache can be used for the lower key frame tracking.


  4,096 * 1024 => 4m,194k,304
  4,194,304 * 1024 => 4g,294m,967k,296
  4,294,967,296 * 1024 => 4t,398g,046m,511k,104 -> 4TB
  4,398,046,511,104 * 1024 => 4p,503t,599g,627m,370k,496


'''



# Data manages mmap and fobj. Cursor does not manage mmap or fobj.
class FileData(Data):

    def __init__(self, path: Optional[str] = None) -> None:
        if not path or not os.path.exists(path):
            raise ValueError("path must be a string that points to a valid file path")
        self._path = path

        self.length = None
        self._fobj = open(path, "rb")

        fd = self._fobj.fileno()
        st = os.fstat(fd)
        if stat.S_ISREG(st.st_mode):
            self.length = st.st_size

    # Read data ahead without progressing cursor.
    def peek(self, cursor: Cursor, length: int) -> bytes:
        self._fobj.seek(cursor.tell(), os.SEEK_SET)
        return self._fobj.read(length)

    # Progress cursor without reading (no copy).
    def seek(self, cursor: Cursor) -> int:
        self._fobj.seek(cursor.tell(), os.SEEK_SET)
        return cursor.tell()

    # Read the data.
    def read(self, cursor: Cursor, length: int) -> bytes:
        self.seek(cursor)
        return self._fobj.read(length)

    # extraction = Extraction.from_xml("<job />")
    @classmethod
    def from_xml(cls, xml_src: Any) -> FileData: # -> cls:
        from thirdparty.pparse._xml import XmlNode, XmlEntry
        xml = XmlNode.as_node(xml_src)

        # Do we have the correct node?
        if not xml.has_tag('datasource'):
            raise Exception(f"Expected datasource node. Got: {xml.get_el().tag}")

        extra = XmlEntry.as_map(xml.extra)
        # TODO: Handle non-posix paths
        if not ('posix_path' in extra or 'windows_path' in extra):
            raise Exception("FileData expected to have one of: posix_path, windows_path")
        path = extra['posix_path']

        data = cls(path)
        if data.length != extra['length']:
            raise Exception(f"Mismatch of length on import of {path}: xml length {extra['length']} real length {data.length}.")

        # Let the XML tree hold the reference
        xml.set_obj_inst(data)

        return data

    # extraction.to_xml() -> "<job />"
    def to_xml(self) -> str:
        raise NotImplementedError("to_xml not implemented")


# Data manages mmap and fobj. Cursor does not manage mmap or fobj.
class FileMmapData(Data):
    def __init__(self, path: Optional[str] = None) -> None:
        if not path or not os.path.exists(path):
            raise ValueError("path must be a string that points to a valid file path")
        self._path = path

        self.length = None
        self._fobj = open(path, "rb")
        self._load_length()

        # Mmap, if available.
        if not has_mmap():
            raise Exception("No mmap available.")

        self._mmap = mmap.mmap(self._fobj.fileno(), 0, access=mmap.ACCESS_READ)
        self._mem = memoryview(self._mmap)

    def _load_length(self) -> None:
        # TODO: This size is only relevant if the size doesn't change.
        fd = self._fobj.fileno()
        st = os.fstat(fd)

        if stat.S_ISREG(st.st_mode):
            self.length = st.st_size

    # Read data ahead without progressing cursor.
    def peek(self, cursor: Cursor, length: int) -> memoryview:
        off = cursor.tell()
        return self._mem[off : off + length]

    # Progress cursor without reading (no copy).
    def seek(self, cursor: Cursor) -> int:
        # Noop for mmap.
        return cursor.tell()

    # Read the data.
    def read(self, cursor: Cursor, length: int, mode: Any = None) -> memoryview:
        off = cursor.tell()
        return self._mem[off : off + length]


# When working with data that is already (reasonably) in memory, we may want to use it as a
# data source. Having that use case in its own class permits us to handle that without extra
# conditions. Mostly the same as FileData, but understood to be in memory.
#
# Real World Use Case: File-format is a ZIP and the header is a file in the ZIP.
#
class BytesIoData(Data):
    def __init__(self, bytes_io: Optional[io.BytesIO] = None) -> None:
        if not bytes_io or not isinstance(bytes_io, io.BytesIO):
            raise ValueError("bytes_io must be io.BytesIO and not be None")

        self._bytes_io = bytes_io
        self.length = len(self._bytes_io.getbuffer())

    def _load_length(self) -> None:
        pass

    # Create a cursor, like a logical file descriptor.
    def open(self, offset: int = 0) -> Cursor:
        return Cursor(self, offset)

    # Read data ahead without progressing cursor.
    def peek(self, cursor: Cursor, length: int) -> bytes:
        self._bytes_io.seek(cursor.tell(), os.SEEK_SET)
        return self._bytes_io.read(length)

    # Progress cursor without reading (no copy).
    def seek(self, cursor: Cursor) -> int:
        self._bytes_io.seek(cursor.tell(), os.SEEK_SET)
        return cursor.tell()

    # Read the data.
    def read(self, cursor: Cursor, length: int) -> bytes:
        self.seek(cursor)
        return self._bytes_io.read(length)

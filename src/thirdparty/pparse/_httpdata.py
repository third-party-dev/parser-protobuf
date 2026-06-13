from __future__ import annotations

import collections
import requests
from typing import Any, Optional, Union


LINKED_LIST_THRESHOLD: int = 1000


class DequeLRUCache:
    def __init__(self, maxsize: int) -> None:
        self._maxsize: int = maxsize
        self._cache: dict[Any, Any] = {}
        self._order: collections.deque[Any] = collections.deque()


    def __contains__(self, key: Any) -> bool:
        return key in self._cache


    def __getitem__(self, key: Any) -> Any:
        self._order.remove(key)
        self._order.append(key)
        return self._cache[key]


    def __setitem__(self, key: Any, value: Any) -> None:
        if key in self._cache:
            self._order.remove(key)
        elif len(self._cache) >= self._maxsize:
            del self._cache[self._order.popleft()]
        self._cache[key] = value
        self._order.append(key)



class LRUCacheEntry:
    # Pythonic memory optimization
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: Any, value: Any) -> None:
        self.key: Any = key
        self.value: Any = value
        self.prev: Optional[LRUCacheEntry] = None
        self.next: Optional[LRUCacheEntry] = None



class LinkedListLRUCache:
    def __init__(self, maxsize: int) -> None:
        self._maxsize: int = maxsize
        self._cache: dict[Any, LRUCacheEntry] = {}
        self._head: LRUCacheEntry = LRUCacheEntry(None, None)
        self._tail: LRUCacheEntry = LRUCacheEntry(None, None)
        self._head.next = self._tail
        self._tail.prev = self._head


    def _remove(self, node: LRUCacheEntry) -> None:
        node.prev.next = node.next
        node.next.prev = node.prev


    def _push(self, node: LRUCacheEntry) -> None:
        node.prev = self._tail.prev
        node.next = self._tail
        self._tail.prev.next = node
        self._tail.prev = node


    def __contains__(self, key: Any) -> bool:
        return key in self._cache


    def __getitem__(self, key: Any) -> Any:
        node = self._cache[key]
        self._remove(node)
        self._push(node)
        return node.value


    def __setitem__(self, key: Any, value: Any) -> None:
        if key in self._cache:
            node = self._cache[key]
            node.value = value
            self._remove(node)
            self._push(node)
            return
        if len(self._cache) >= self._maxsize:
            oldest = self._head.next
            self._remove(oldest)
            del self._cache[oldest.key]
        node = LRUCacheEntry(key, value)
        self._cache[key] = node
        self._push(node)



def _get_cache(maxsize: int) -> Union[LinkedListLRUCache, DequeLRUCache]:
    if maxsize > LINKED_LIST_THRESHOLD:
        return LinkedListLRUCache(maxsize)
    return DequeLRUCache(maxsize)




class _HttpCachedData:
    def __init__(self, url: str, chunk_size: int = 4096, chunk_max_count: int = 256, session: Optional[requests.Session] = None) -> None:
        self._url: str = url
        self._chunk_size: int = chunk_size
        self._cache: Union[LinkedListLRUCache, DequeLRUCache] = _get_cache(chunk_max_count)
        self._session: requests.Session = session or requests.Session()
        self._length: int = self._load_length()


    def _load_length(self) -> int:
        response = self._session.head(self._url)
        response.raise_for_status()
        return int(response.headers["Content-Length"])


    def __len__(self) -> int:
        return self._length


    # Assumes Range header supported.
    # def _fetch_chunk(self, chunk_idx: int) -> bytes:
    #     start = chunk_idx * self._chunk_size
    #     end = min(start + self._chunk_size, len(self)) - 1
    #     r = self._session.get(self._url, headers={"Range": f"bytes={start}-{end}"})
    #     r.raise_for_status()
    #     return r.content


    def _fetch_chunk(self, chunk_idx: int) -> bytes:
        start = chunk_idx * self._chunk_size
        end = min(start + self._chunk_size, len(self)) - 1
        response = self._session.get(self._url, headers={"Range": f"bytes={start}-{end}"})
        response.raise_for_status()

        if response.status_code == 206:
            return response.content

        if response.status_code == 200:
            # Range was not honoured — we got the full file body.
            # Take advantage by populating as many chunks as we can
            # around the requested chunk_idx.
            data = response.content

            # How many complete chunks do we have?
            total_chunks = (len(data) + self._chunk_size - 1) // self._chunk_size

            # Work out a window of chunks to cache: one behind, rest forward.
            cache_start = max(0, chunk_idx - 1)
            cache_end = total_chunks  # exclusive

            for i in range(cache_start, cache_end):
                lo = i * self._chunk_size
                hi = min(lo + self._chunk_size, len(data))
                self._cache[i] = data[lo:hi]

            # return self._cache[chunk_idx]
            lo = chunk_idx * self._chunk_size
            hi = min(lo + self._chunk_size, len(data))
            return data[lo:hi]

        raise IOError(f"Unexpected status {response.status_code}")


    def _get_chunk(self, chunk_idx: int) -> bytes:
        if chunk_idx not in self._cache:
            self._cache[chunk_idx] = self._fetch_chunk(chunk_idx)
        return self._cache[chunk_idx]


    # Potentially lots of realloc
    # def _read(self, offset: int, length: int) -> bytes:
    #     if length <= 0:
    #         return b''

    #     # Optional guard against reading more than cache.
    #     # max_readable = self._chunk_max_count * self._chunk_size
    #     # if length > max_readable:
    #     #     raise ValueError(f"Requested {length} bytes exceeds cache capacity.")

    #     result = bytearray()
    #     start_idx = offset // self._chunk_size
    #     end_idx = (offset + length - 1) // self._chunk_size

    #     for chunk_idx in range(start_idx, end_idx + 1):
    #         chunk = self._get_chunk(chunk_idx)
    #         chunk_start = chunk_idx * self._chunk_size
    #         lo = max(offset, chunk_start) - chunk_start
    #         hi = min(offset + length, chunk_start + len(chunk)) - chunk_start
    #         result += chunk[lo:hi]

    #     return bytes(result)

    

    def _read(self, offset: int, length: int) -> bytes:
        if length <= 0:
            return b''

        # Optional guard against reading more than cache.
        # max_readable = self._chunk_max_count * self._chunk_size
        # if length > max_readable:
        #     raise ValueError(f"Requested {length} bytes exceeds cache capacity.")

        start_idx = offset // self._chunk_size
        end_idx   = (offset + length - 1) // self._chunk_size

        # If the request doesn't cross chunk boundary, return as is.
        if start_idx == end_idx:
            chunk = self._get_chunk(start_idx)
            lo = offset - start_idx * self._chunk_size
            return memoryview(chunk)[lo:lo + length].tobytes()

        # When cross the boundary, (without an MMU :( ), must copy-to result.
        available = min(length, max(0, len(self) - offset))
        result = bytearray(available)  # best-guess pre-allocation
        written = 0

        for chunk_idx in range(start_idx, end_idx + 1):
            chunk = self._get_chunk(chunk_idx)
            chunk_start = chunk_idx * self._chunk_size
            lo = max(offset, chunk_start) - chunk_start
            hi = min(offset + length, chunk_start + len(chunk)) - chunk_start
            slice_len = hi - lo
            if slice_len <= 0:
                break
            result[written:written + slice_len] = chunk[lo:hi]
            written += slice_len

        return bytes(result[:written])


    def __getitem__(self, key: Union[slice, int]) -> bytes:
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            data = self._read(start, stop - start)
            return data[::step] if step != 1 else data

        if isinstance(key, int):
            if key < 0:
                key += len(self)
            if not (0 <= key < len(self)):
                raise IndexError(key)
            return self._read(key, 1)

        raise TypeError('Index must be an int or slice.')
"""
@Author:TioitWang
@E-mile:me@tioit.cc
@CreateTime:2022/6/8-11:06
@DependencyLibrary:[...]
@MainFunction:None
@FileDoc:
    locmem is python file
@ChangeHistory:
    datetime action why
    2022/6/8-11:06 [Create] locmem.py
"""
import pickle
import time
from asyncio import Lock
from collections import OrderedDict

from rest_framework.cache.backends.base import DEFAULT_TIMEOUT, BaseCache

# from threading import Lock

_caches = {}
_expire_info = {}
_locks = {}


class LocMemCache(BaseCache):
    pickle_protocol = pickle.HIGHEST_PROTOCOL

    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = _caches.setdefault(name, OrderedDict())
        self._expire_info = _expire_info.setdefault(name, {})
        self._lock = _locks.setdefault(name, Lock())
        self._cull_frequency = 0
        self._max_entries = 300

    async def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_cache_key(key, version=version)
        pickled = pickle.dumps(value, self.pickle_protocol)
        async with self._lock:
            if self._has_expired(key):
                await self._set(key, pickled, timeout)
                return True
            return False

    async def get(self, key, default=None, version=None):
        key = self.make_cache_key(key, version=version)
        async with self._lock:
            if self._has_expired(key):
                await self._delete(key)
                return default
            pickled = self._cache[key]
            self._cache.move_to_end(key, last=False)
        return pickle.loads(pickled)

    async def _set(self, key, value, timeout=DEFAULT_TIMEOUT):
        if len(self._cache) >= self._max_entries:
            await self._cull()
        self._cache[key] = value
        self._cache.move_to_end(key, last=False)
        self._expire_info[key] = time.time() + timeout

    async def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_cache_key(key, version=version)
        pickled = pickle.dumps(value, self.pickle_protocol)
        async with self._lock:
            await self._set(key, pickled, timeout)

    async def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_cache_key(key, version=version)
        async with self._lock:
            if self._has_expired(key):
                return False
            self._expire_info[key] = time.time() + timeout
            return True

    async def incr(self, key, delta=1, version=None):
        key = self.make_cache_key(key, version=version)
        async with self._lock:
            if self._has_expired(key):
                await self._delete(key)
                raise ValueError("Key '%s' not found" % key)
            pickled = self._cache[key]
            value = pickle.loads(pickled)
            new_value = value + delta
            pickled = pickle.dumps(new_value, self.pickle_protocol)
            self._cache[key] = pickled
            self._cache.move_to_end(key, last=False)
        return new_value

    async def has_key(self, key, version=None):
        key = self.make_cache_key(key, version=version)
        async with self._lock:
            if self._has_expired(key):
                await self._delete(key)
                return False
            return True

    def _has_expired(self, key):
        exp = self._expire_info.get(key, -1)
        return exp is not None and exp <= time.time()

    async def _cull(self):
        if self._cull_frequency == 0:
            self._cache.clear()
            self._expire_info.clear()
        else:
            count = len(self._cache) // self._cull_frequency
            for i in range(count):
                key, _ = self._cache.popitem()
                del self._expire_info[key]

    async def _delete(self, key):
        try:
            del self._cache[key]
            del self._expire_info[key]
        except KeyError:
            return False
        return True

    async def delete(self, key, version=None):
        key = self.make_cache_key(key, version=version)
        async with self._lock:
            return self._delete(key)

    async def clear(self):
        async with self._lock:
            self._cache.clear()
            self._expire_info.clear()

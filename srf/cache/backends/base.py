"""
@Author:WangYuXiang
@E-mile:Hill@3io.cc
@CreateTime:2022/6/8-10:50
@DependencyLibrary:[...]
@MainFunction:None
@FileDoc: 
    backends is python file
@ChangeHistory:
    datetime action why
    2022/6/8-10:50 [Create] backends.py
"""
DEFAULT_TIMEOUT = 300
CACHE_MAX_ENTRIES = 300
DEFAULT_VERSION = 1


class BaseCache:
    def __init__(self, timeout=DEFAULT_TIMEOUT, max_entries=CACHE_MAX_ENTRIES, key_prefix=None):
        self.default_timeout = timeout
        self._max_entries = max_entries
        if key_prefix is None:
            key_prefix = ''
        self.key_prefix = key_prefix

    def make_cache_key(self, key, version=None):
        if version is None:
            version = DEFAULT_VERSION
        return "%s:%s:%s" % (self.key_prefix, version, key)

    async def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Set a value in the cache if the key does not already exist. If
        timeout is given, use that timeout for the key; otherwise use the
        default cache timeout.
        Return True if the value was stored, False otherwise.
        """
        raise NotImplementedError("subclasses of BaseCache must provide an add() method")

    async def get(self, key, default=None, version=None):
        """
        Fetch a given key from the cache. If the key does not exist, return
        default, which itself defaults to None.
        """
        raise NotImplementedError("subclasses of BaseCache must provide a get() method")

    async def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Set a value in the cache. If timeout is given, use that timeout for the
        key; otherwise use the default cache timeout.
        """
        raise NotImplementedError("subclasses of BaseCache must provide a set() method")

    async def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Update the key's expiry time using timeout. Return True if successful
        or False if the key does not exist.
        """
        raise NotImplementedError("subclasses of BaseCache must provide a touch() method")

    async def delete(self, key, version=None):
        """
        Delete a key from the cache and return whether it succeeded, failing
        silently.
        """
        raise NotImplementedError("subclasses of BaseCache must provide a delete() method")

    async def clear(self):
        """Remove *all* values from the cache at once."""
        raise NotImplementedError("subclasses of BaseCache must provide a clear() method")

    async def incr(self, key, delta=1, version=None):
        """Add delta to the value of the key."""
        raise NotImplementedError("subclasses of BaseCache must provide a incr() method")

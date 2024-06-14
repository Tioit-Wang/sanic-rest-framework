"""
@Author: TioitWang
@E-mile: me@tioit.cc
@CreateTime: 2022/6/8-17:51
@DependencyLibrary: [...]
@MainFunction: None
@FileDoc:
    core is python file
@ChangeHistory:
    datetime action why
    2022/6/8-17:51 [Create] core.py
"""
import hashlib
from functools import wraps

from rest_framework.cache.backends import cache


def mark_key(module, path, method):
    path_hash = hashlib.md5(path.encode('utf8')).hexdigest()
    return '.'.join([module, path_hash, method])


def api_cache(timeout, cache_backend=None, include_query=False):
    """
    cache the return value of the view, you can use a custom cache_backend.
    If include_query is True, then the cached key will contain query_string
    @param timeout: In seconds
    @param cache_backend: Cache backend is based on BaseCache
    @param include_query: Does it include query_string?
    @return:
    """
    if cache_backend is None:
        cache_backend = cache

    def decorator_func(func):
        @wraps(func)
        async def wrapper(view, request, *args, **kwargs):
            if include_query:
                path = request.raw_url.decode('utf8')
            else:
                path = request.path
            key = mark_key(request.endpoint, path, request.method)
            if await cache_backend.has_key(key):
                return await cache_backend.get(key)
            rs = await func(view, request, *args, **kwargs)
            await cache_backend.set(key, rs, timeout)
            return rs

        return wrapper

    return decorator_func

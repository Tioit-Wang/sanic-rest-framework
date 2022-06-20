"""
@Author:WangYuXiang
@E-mile:Hill@3io.cc
@CreateTime:2022/6/8-11:06
@DependencyLibrary:[...]
@MainFunction:None
@FileDoc: 
    __init__.py is python file
@ChangeHistory:
    datetime action why
    2022/6/8-11:06 [Create] __init__.py.py
"""
from srf.cache.backends.locmem import LocMemCache

DEFAULT_CACHE_ALIAS = "default"
cache = LocMemCache(DEFAULT_CACHE_ALIAS)

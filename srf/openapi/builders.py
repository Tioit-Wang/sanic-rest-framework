"""
@Author: WangYuXiang
@E-mile: Hill@3io.cc
@CreateTime: 2022/6/14-17:32
@DependencyLibrary: [...]
@MainFunction: None
@FileDoc: 
    builders is python file
@ChangeHistory: 
    datetime action why
    2022/6/14-17:32 [Create] builders.py
"""
from typing import Any


class OpenAPIStore(dict):
    _singleton = None

    def __new__(cls) -> Any:
        if not cls._singleton:
            cls._singleton = super().__new__(cls)
        return cls._singleton

    def add(self, api_key, key, value):
        if api_key not in self:
            self[api_key] = {}
        self[api_key][key] = value

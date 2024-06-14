# -*- coding: utf-8 -*-
# @Date : Fri May 31 2024
# @Author : v_wyxgwang
# @File : __init__.py.py
# @Software: VSCode
from collections import defaultdict
from typing import Any

from rest_framework.openapi3.builders import OperationBuilder, SpecificationBuilder


class OperationStore(defaultdict):
    _singleton = None

    def __new__(cls, *args, **kwargs) -> Any:
        if not cls._singleton:
            cls._singleton = super().__new__(cls, *args, **kwargs)
        return cls._singleton


operations = OperationStore(OperationBuilder)
specification = SpecificationBuilder()

from .blueprint import blueprint_factory  # noqa


openapi3_blueprint = blueprint_factory()

"""
@Author:TioitWang
@E-mile:me@tioit.cc
@CreateTime:2021/3/11 16:59
@DependencyLibrary:无
@MainFunction:无
@FileDoc:
    utils.py
    文件说明
@ChangeHistory:
    datetime action why
    example:
    2021/3/11 16:59 change 'Fix bug'
"""
import datetime
import functools
import inspect
from decimal import Decimal
from urllib import parse

from tortoise.exceptions import IntegrityError

from rest_framework.exceptions import APIException

_PROTECTED_TYPES = (
    type(None), int, float, Decimal, datetime.datetime, datetime.date, datetime.time,
)


class ObjectDict(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        if isinstance(value, dict):
            self[key] = ObjectDict(value)
        self[key] = value


def is_protected_type(obj):
    """确定对象实例是否为受保护的类型。
    受保护类型的对象在传递给时会原样保留
    force_str(strings_only = True)。
    """
    return isinstance(obj, _PROTECTED_TYPES)


def force_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    与smart_str()类似，除了将懒实例解析为
    字符串，而不是保留为惰性对象。
    如果strings_only为True，请不要转换（某些）非字符串类对象。
    """
    # 出于性能原因，请先处理常见情况。
    if issubclass(type(s), str):
        return s
    if strings_only and is_protected_type(s):
        return s
    try:
        s = str(s, encoding, errors) if isinstance(s, bytes) else str(s)
    except UnicodeDecodeError as e:
        raise APIException('{value}出现解码错误'.format(value=s))
    return s


def replace_query_param(url, key, val):
    """
    给定一个URL和一个键/值对，在URL的查询参数中设置或替换一个项目，然后返回新的URL。
    """
    (scheme, netloc, path, query, fragment) = parse.urlsplit(force_str(url))
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict[force_str(key)] = [force_str(val)]
    query = parse.urlencode(sorted(list(query_dict.items())), doseq=True)
    return parse.urlunsplit((scheme, netloc, path, query, fragment))


class IntegrityErrorHandel:
    def __init__(self, exc: IntegrityError):
        self.exc = exc
        self.message = str(exc)

    def parse_error_str(self):
        error = '发生错误:{}{}'
        if 'UNIQUE' in self.message:
            field_name = self.message.split('.')[-1]
            error = error.format(field_name, '已存在')
        return error

    def __str__(self):
        return self.parse_error_str()


async def run_awaitable(func, *args, **kwargs):
    return await func(*args, **kwargs) if inspect.iscoroutinefunction(func) else func(*args, **kwargs)


async def run_awaitable_val(value):
    return (await value) if inspect.isawaitable(value) else value


def is_callable(obj):
    return bool(inspect.isfunction(obj) or inspect.ismethod(obj) or isinstance(obj, functools.partial))

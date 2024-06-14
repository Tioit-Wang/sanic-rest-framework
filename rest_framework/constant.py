"""
@Author: TioitWang
@E-mile: me@tioit.cc
@CreateTime: 2021/1/19 15:45
@DependencyLibrary: 无
@MainFunction:无
@FileDoc:
    constant.py
    全局常量
"""
from enum import IntEnum

ALL_METHOD = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}
DETAIL_METHOD_GROUP = {
    'dynamic_method': ('GET', 'PUT', 'DELETE', 'PATCH'),
    'static_method': ('POST', 'OPTION')
}
LIST_METHOD_GROUP = {
    'dynamic_method': ('PUT', 'DELETE', 'PATCH'),
    'static_method': ('GET', 'POST', 'OPTION')
}
DEFAULT_METHOD_MAP = {'get': 'get', 'post': 'post', 'put': 'put',
                      'patch': 'patch', 'delete': 'delete', 'head': 'head', 'options': 'options'}

LOOKUP_SEP = '__'

LIST_SERIALIZER_KWARGS = (
    'read_only',
    'write_only',
    'required',
    'allow_null',
    'default',
    'source',
    'validators',
    'error_messages',
    'label',
    'description',
    'instance',
    'data',
    'partial'
)
ALL_FIELDS = '__all__'

DEFAULT_NESTED_DEPTH = 1


class BoolEnum(IntEnum):
    """布尔枚举"""
    FALSE = 0
    TRUE = 1

"""
@Author：WangYuXiang
@E-mile：Hill@3io.cc
@CreateTime：2021/1/22 10:41
@DependencyLibrary：无
@MainFunction：无
@FileDoc： 
    validators.py
    文件说明
@ChangeHistory:
    datetime action why
    example:
    2021/1/22 10:41 change 'Fix bug'
        
"""
import copy
from typing import Dict

from srf.exceptions import ValidationException, ValidatorAssertError

__all__ = ['BaseValidator', 'MaxLengthValidator', 'MinLengthValidator', 'MaxValueValidator', 'MinValueValidator']


class BaseValidator:
    """验证器基类
    所有通用验证器都需要继承本类，
    在调用 __call__ 时抛出 ValidationException 错误
    即代表验证失败
    """
    default_error_messages: Dict[str, str] = {

    }

    def __init__(self, error_messages: Dict[str, str] = None, code=None):
        self.error_messages = copy.copy(self.default_error_messages)
        if error_messages is not None:
            self.error_messages.update(copy.copy(error_messages))
        self.code = code

    def __call__(self, value, serializer=None):
        raise NotImplementedError('验证器必须重新定义 __call__()')

    def raise_error(self, key, **kws):
        msg = self.default_error_messages[key].format(**kws)
        raise ValidationException(msg, code=key)


class MaxLengthValidator(BaseValidator):
    default_error_messages: Dict[str, str] = {
        'max_length': '超出长度，最长支持{max_length}',
        'invalid': '无效的数据类型，数据类型只支持{datatypes}'
    }

    def __init__(self, max_length, **kwargs):
        if not isinstance(max_length, (int, float)):
            raise ValidatorAssertError('max_length的值只支持数值类型')
        self.max_length = max_length

        super(MaxLengthValidator, self).__init__(**kwargs)

    def __call__(self, value, serializer=None):
        if not isinstance(value, (str, list, dict, type)):
            self.raise_error('invalid', datatypes='str, list, dict, type')

        if len(value) > self.max_length:
            self.raise_error('max_length', max_length=self.max_length)


class MinLengthValidator(BaseValidator):
    default_error_messages: Dict[str, str] = {
        'min_length': '低于最低长度，最低为 {min_length}',
        'invalid': '无效的数据类型，数据类型只支持 {datatypes} '

    }

    def __init__(self, min_length, **kwargs):
        if not isinstance(min_length, (int, float)):
            raise ValidatorAssertError('min_length的值只支持数值类型')

        self.min_length = min_length
        super(MinLengthValidator, self).__init__(**kwargs)

    def __call__(self, value, serializer=None):
        if not isinstance(value, (str, list, dict, type)):
            self.raise_error('invalid', datatypes='str, list, dict, type')

        if len(value) < self.min_length:
            self.raise_error('min_length', min_length=self.min_length)


class MaxValueValidator(BaseValidator):
    default_error_messages: Dict[str, str] = {
        'max_value': '超出最大值，最大值支持到{max_value}',
        'invalid': '无效的数据类型，数据类型只支持{datatypes}'

    }

    def __init__(self, max_value, **kwargs):
        if not isinstance(max_value, (int, float)):
            raise ValidatorAssertError('max_value的值只支持数值类型')
        self.max_value = max_value
        super(MaxValueValidator, self).__init__(**kwargs)

    def __call__(self, value, serializer=None):
        if not isinstance(value, (int, float)):
            self.raise_error('invalid', datatypes='int, float')

        if value > self.max_value:
            self.raise_error('max_value', max_value=self.max_value)


class MinValueValidator(BaseValidator):
    default_error_messages: Dict[str, str] = {
        'min_value': '低于最小值，最小值至少要为{min_value}',
        'invalid': '无效的数据类型，数据类型只支持{datatypes}'
    }

    def __init__(self, min_value, **kwargs):
        if not isinstance(min_value, (int, float)):
            raise ValidatorAssertError('min_value的值只支持数值类型')
        self.min_value = min_value
        super(MinValueValidator, self).__init__(**kwargs)

    def __call__(self, value, serializer=None):
        if not isinstance(value, (int, float)):
            self.raise_error('invalid', datatypes='int, float')

        if value < self.min_value:
            self.raise_error('min_value', min_value=self.min_value)

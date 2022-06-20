"""
@Author: WangYuXiang
@E-mile: Hill@3io.cc
@CreateTime: 2021/1/20 13:20
@DependencyLibrary:
@MainFunction:
@FileDoc:
    fields.py
    文件说明
"""
import copy
import decimal
import inspect
import re
from collections import OrderedDict
from datetime import timezone, timedelta, datetime, date, time
from enum import Enum
from typing import Any, List, Mapping

from tortoise.exceptions import DoesNotExist

from srf.exceptions import ValidationException
from srf.openapi.openapi import PropItem
from srf.utils import is_callable, run_awaitable, run_awaitable_val
from srf.validators import (
    MaxLengthValidator, MinLengthValidator, MaxValueValidator, MinValueValidator
)

REGEX_TYPE = type(re.compile(''))

__all__ = ('empty', 'SkipField', 'Field', 'CharField', 'IntegerField', 'FloatField', 'DecimalField', 'BooleanField',
           'DateTimeField', 'DateField', 'TimeField', 'ChoiceField', 'EnumChoiceField', 'RelatedField',
           'PrimaryKeyRelatedField', 'ManyRelatedField', 'SlugRelatedField')


class empty:
    """
    此类代表空，因为有些字段可以为 None
    所以需要一个可以替代 None 代表空变量
    """
    pass


class SkipField(Exception):
    pass


NOT_RAED_ONLY_AND_WRITE_ONLY = 'May not set both `read_only` and `write_only`'
NOT_RAED_ONLY_REQUIRED_ONLY = 'May not set both `read_only` and `required`'


class Field:
    """字段及序列化器基类
        required: 反序列化时是否必须存在，值限制写入时
        allow_null: 是否可以为 None 即存在当没值

    """
    _doc_type = 'string'
    _doc_format = None

    _sort_counter = 0
    # 所有field都强制拥有的错误提示
    base_error_messages = {
        'required': '此字段为必填项，提交时必须携带',
        'null': '此字段不能为空',
    }
    default_error_messages = None

    default_validators = None

    def __init__(self, read_only=False, write_only=False, required=None, allow_null=False,
                 default=empty, source=None, validators=None, error_messages=None,
                 label=None, description=None):
        """
        字段及field的基类
        :param read_only: 只序列化
        :param write_only: 只反序列化
        :param required: 反序列化时必须存在此值
        :param allow_null: 反序列化时可以为 None, ''
        :param default: 默认值 可用于序列化和反序列化
        :param source: 序列化时值的来源
        :param validators: 反序列化时数据需要通过的验证
        :param error_messages: 出现错误时的自定义描述
        :param label: 字段标题
        :param description: 字段描述
        """
        assert not (read_only and write_only), NOT_RAED_ONLY_AND_WRITE_ONLY
        assert not (read_only and required), NOT_RAED_ONLY_REQUIRED_ONLY
        if required is None and (not read_only or write_only):
            required = True
        self._sort_counter = Field._sort_counter
        Field._sort_counter += 1

        self.read_only = read_only
        self.write_only = write_only
        self.required = required
        self.allow_null = allow_null
        self.default = default
        self.source = source
        self.label = label
        self.description = description

        self.validators = self.collect_validators([validators, self.default_validators])
        self.error_messages = self.collect_error_message(
            [self.base_error_messages, self.default_error_messages, error_messages])

        self.field_name = None
        self.parent = None

    def _doc_properties(self):
        title = self.label if self.label else self.field_name

        return PropItem(title, self._doc_type, self._doc_format).to_dict()

    def __new__(cls, *args, **kwargs):
        """
        当一个字段被实例化时，我们存储所使用的参数，
        这样我就可以在 __deepcopy__ 提供他们
        """
        instance = super().__new__(cls)
        instance._args = args
        instance._kwargs = kwargs
        return instance

    def __deepcopy__(self, memo):
        """
        当克隆字段时，我们使用参数实例化它
        最初创建时用的，而不是复制完整的状态。
        """
        args = [
            copy.deepcopy(item) if not isinstance(item, REGEX_TYPE) else item
            for item in self._args
        ]
        kwargs = {
            key: (copy.deepcopy(value, memo) if (key not in ('validators', 'regex')) else value)
            for key, value in self._kwargs.items()
        }
        return self.__class__(*args, **kwargs)

    def bind(self, field_name, parent):
        """
        提供给父级的绑定
        :param field_name:
        :param parent:
        :return:
        """
        self.field_name = field_name
        self.parent = parent

        if self.source is None:
            self.source = self.field_name

        if self.source == '*':
            self.source_attrs = []
        else:
            self.source_attrs = self.source.split('.')

    def collect_error_message(self, error_messages_list: List[dict]) -> dict:
        """
        收集错误提示
        :param error_messages_list: 错误提示列表
        :return:
        """
        error_messages = {}
        for error_message in error_messages_list:
            if error_message is not None:
                error_messages.update(error_message)
        return error_messages

    def collect_validators(self, validators_list: List[list]) -> list:
        """
        收集所有验证器
        :param validators_list: 验证器列表
        :return:
        """
        validators = []
        for validator_list in validators_list:
            if validator_list is not None:
                for validator in validator_list:
                    if validator not in validators:
                        validators.append(validator)
        return validators

    def is_partial(self, root=None):
        """当请求为部分修改的时候,返回 True """
        if root is None:
            root = self.root
        return getattr(root, 'partial', False)

    async def external_to_internal(self, data: Any) -> Any:
        """对数据进行反序列化转换并返回"""
        raise NotImplementedError(
            'subclasses of {cls} must provide a external_to_internal() method'.format(cls=self.__class__.__name__, )
        )

    async def internal_to_external(self, data: Any) -> Any:
        """对数据进行序列化转换并返回"""
        raise NotImplementedError(
            'subclasses of {cls} must provide a internal_to_external() method'.format(cls=self.__class__.__name__, )
        )

    def get_external_value(self, data: Mapping) -> Any:
        """
        从传入的外部数据中得到值
        值用于输入验证
        :param data: *外部* 数据
        :return:
        """
        if not isinstance(data, Mapping):
            raise ValidationException('传入的数据为无效数据类型，仅支持字典类型'.format(self.field_name))
        if self.field_name not in data:
            if self.is_partial():
                return empty
            return self.default
        value = data.get(self.field_name)
        return value

    async def get_internal_value(self, instance: Any) -> Any:
        """
        从传入的内部数据中得到值
        值用于输出
        :param instance: *内部* 数据
        :return:
        """
        for attr in self.source_attrs:
            # 取值后可能为空，不能继续取
            if instance is None:
                return None
            # 不为空再取值
            try:
                if isinstance(instance, Mapping):
                    instance = instance[attr]
                else:
                    instance = getattr(instance, attr)
                    if is_callable(instance):
                        instance = await run_awaitable(instance)
                    else:
                        instance = await run_awaitable_val(instance)
            except DoesNotExist:
                return None
            except (KeyError, AttributeError) as exc:
                if self.default is not empty:
                    return self.default
                if self.allow_null:
                    return None
                if not self.required:
                    raise SkipField()
                raise type(exc)('在序列化过程中字段{field_name}未能成功序列化'.format(field_name=self.field_name))
        return instance

    def run_validators(self, data) -> None:
        """
        使用验证器验证传入的数据
        直接抛出错误
        :param data:
        :return: 无返回值
        """
        errors = []
        for validator in self.validators:
            try:
                validator(data, self)
            except ValidationException as exc:
                errors.extend(exc.error_detail)
        if errors:
            raise ValidationException(errors)

    def get_default(self):
        """得到默认值"""
        if self.default is empty or getattr(self.root, 'partial', False):
            raise SkipField()
        if callable(self.default):
            return self.default()
        return self.default

    def validate_empty_values(self, data):
        """
        判断是否为空值
        :param data: Any
        :return: (bool,Any) => (是否为空  ,data)
        """
        if self.read_only:
            return True, self.get_default()
        if data is empty:
            #
            if self.is_partial():
                raise SkipField()
            if self.required:
                self.raise_error('required')
            return True, self.get_default()

        if data is None:
            if not self.allow_null:
                self.raise_error('null')
            elif self.source == '*':
                return False, None
            return True, None
        return (False, data)

    async def run_validation(self, data):
        """执行验证"""
        (is_empty_value, data) = self.validate_empty_values(data)
        if is_empty_value:
            return data
        value = await self.external_to_internal(data)
        self.run_validators(value)
        return value

    @property
    def root(self):
        """
        得到字段的最高级父级
        """
        root = self
        while root.parent is not None:
            root = root.parent
        return root

    @property
    def context(self):
        """
        返回初始化时传递给根序列化程序的上下文。
        """
        return getattr(self.root, '_context', {})

    def raise_error(self, _key, **kwargs):
        """
        返回在 error_messages 中注册了的错误
        :param _key: 错误的键
        :param kwargs:
        :return:
        """
        try:
            msg = self.error_messages[_key]
        except KeyError:
            class_name = self.__class__.__name__
            msg = 'ValidationError raised by `{class_name}`, but error key `{key}` does ' \
                  'not exist in the `error_messages` dictionary.'.format(class_name=class_name, key=_key)
            raise AssertionError(msg)
        message_string = msg.format(**kwargs)
        raise ValidationException(message_string, code=_key)

    def __str__(self):
        return super(Field, self).__str__() + self.field_name


class CharField(Field):
    """字符字段"""
    default_error_messages = {
        'invalid': 'Must be a valid string.',
        'max_length': 'Ensure this field has no more than {max_length} characters.',
        'min_length': 'The value contains a maximum of {min_length} characters.',
    }

    def __init__(self, *args, **kwargs):
        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)
        self.trim_whitespace = kwargs.pop('trim_whitespace', True)
        super(CharField, self).__init__(*args, **kwargs)
        if self.max_length is not None:
            self.validators.append(MaxLengthValidator(max_length=self.max_length,
                                                      error_messages={'max_length': self.error_messages['max_length']}))
        if self.min_length is not None:
            self.validators.append(MinLengthValidator(min_length=self.min_length,
                                                      error_messages={'min_length': self.error_messages['min_length']}))

    async def external_to_internal(self, data: Any) -> Any:
        if isinstance(data, bool) or not isinstance(data, (str, int, float,)):
            self.raise_error('invalid')
        value = str(data)
        return value.strip() if self.trim_whitespace else value

    async def internal_to_external(self, data: Any) -> Any:
        return str(data)


class IntegerField(Field):
    """整数类型"""

    _doc_type = 'integer'
    _doc_format = 'int64'

    default_error_messages = {
        'invalid': 'Must be a valid integer.',
        'max_value': 'Ensure this value is less than or equal to {max_value}',
        'min_value': 'Ensure this value is greater than or equal to {min_value}',
        'max_string_length': 'String value too large.',
    }
    re_decimal = re.compile(r'\.0*\s*$')
    MAX_STRING_LENGTH = 1000

    def __init__(self, max_value=None, min_value=None, *args, **kwargs):
        self.max_value = max_value
        self.min_value = min_value
        super(IntegerField, self).__init__(*args, **kwargs)
        if self.max_value is not None:
            self.validators.append(MaxValueValidator(max_value=self.max_value,
                                                     error_messages={'max_value': self.error_messages['max_value']}))
        if self.min_value is not None:
            self.validators.append(MinValueValidator(min_value=self.min_value,
                                                     error_messages={'min_value': self.error_messages['min_value']}))

    async def external_to_internal(self, data: Any):
        if isinstance(data, str) and len(data) > self.MAX_STRING_LENGTH:
            self.raise_error('max_string_length')
        try:
            data = int(self.re_decimal.sub('', str(data)))
        except (ValueError, TypeError):
            self.raise_error('invalid')
        return data

    async def internal_to_external(self, data: Any):
        return int(data)


class FloatField(IntegerField):
    """浮点类型"""
    _doc_type = 'number'
    _doc_format = 'float'
    default_error_messages = {
        'invalid': 'Must be a valid float.',
        'max_value': 'Ensure this value is less than or equal to {max_value}',
        'min_value': 'Ensure this value is greater than or equal to {min_value}',
        'max_string_length': 'String value too large.',
    }
    MAX_STRING_LENGTH = 1000

    async def external_to_internal(self, data: Any):
        if isinstance(data, str) and len(data) > self.MAX_STRING_LENGTH:
            self.raise_error('max_string_length')
        try:
            return float(data)
        except (TypeError, ValueError):
            self.raise_error('invalid')

    async def internal_to_external(self, data: Any):
        return float(data)


class DecimalField(Field):
    """十进制类型"""
    _doc_type = 'number'
    _doc_format = 'float'

    default_error_messages = {
        'invalid': 'Must be a valid number.',
        'max_value': 'Ensure this value is less than or equal to {max_value}.',
        'min_value': 'Ensure this value is greater than or equal to {min_value}.',
        'max_string_length': 'String value too large.',
        'max_digits': 'Ensure that there are no more than {max_digits} digits in total.',
        'max_decimal_places': 'Ensure that there are no more than {max_decimal_places} decimal places.',
        'max_whole_digits': 'Ensure that there are no more than {max_whole_digits} digits before the decimal point.',
    }
    MAX_STRING_LENGTH = 1000

    def __init__(self, max_digits, decimal_places, coerce_to_string=False, max_value=None, min_value=None,
                 rounding=None, *args, **kwargs):
        """
        整数位数 = max_digits - decimal_places
        :param max_digits: 数字允许的最大位数
        :param decimal_places: 小数的最大位数
        :param coerce_to_string:
        :param max_value:
        :param min_value:
        :param rounding:
        :param args:
        :param kwargs:
        """
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.coerce_to_string = coerce_to_string
        self.max_value = max_value
        self.min_value = min_value
        self.rounding = rounding
        if self.max_digits is not None and self.decimal_places is not None:
            self.max_whole_digits = self.max_digits - self.decimal_places
        else:
            self.max_whole_digits = None
        super(DecimalField, self).__init__(*args, **kwargs)
        if self.max_value is not None:
            self.validators.append(MaxValueValidator(max_value=self.max_value,
                                                     error_messages={'max_value': self.error_messages['max_value']}))
        if self.min_value is not None:
            self.validators.append(MinValueValidator(min_value=self.min_value,
                                                     error_messages={'min_value': self.error_messages['min_value']}))

    async def external_to_internal(self, data: Any):
        data = str(data).strip()

        if len(data) > self.MAX_STRING_LENGTH:
            self.raise_error('max_string_length')
        try:
            data = decimal.Decimal(data)
        except decimal.DecimalException:
            self.raise_error('invalid')

        if data.is_nan():
            self.raise_error('invalid')

        # 检查无穷大和负无穷大。
        if data in (decimal.Decimal('Inf'), decimal.Decimal('-Inf')):
            self.raise_error('invalid')

        return self.quantize(self.validate_precision(data))

    async def internal_to_external(self, data: Any):
        if not isinstance(data, decimal.Decimal):
            data = decimal.Decimal(str(data).strip())

        quantized = self.quantize(data)

        if not self.coerce_to_string:
            return quantized
        return ('{:%sf}' % self.decimal_places).format(quantized)

    def validate_precision(self, value):
        """
        确保数字中的位数不超过max_digits，并且小数点后超过十进制的位数。
        覆盖此方法以禁用输入的精度验证值或以您需要的任何方式增强它。
        """
        sign, digittuple, exponent = value.as_tuple()

        if exponent >= 0:
            # 1234500.0
            total_digits = len(digittuple) + exponent
            whole_digits = total_digits
            decimal_places = 0
        elif len(digittuple) > abs(exponent):
            # 123.45
            total_digits = len(digittuple)
            whole_digits = total_digits - abs(exponent)
            decimal_places = abs(exponent)
        else:
            # 0.001234
            total_digits = abs(exponent)
            whole_digits = 0
            decimal_places = total_digits

        if self.max_digits is not None and total_digits > self.max_digits:
            self.raise_error('max_digits', max_digits=self.max_digits)
        if self.decimal_places is not None and decimal_places > self.decimal_places:
            self.raise_error('max_decimal_places', max_decimal_places=self.decimal_places)
        if self.max_whole_digits is not None and whole_digits > self.max_whole_digits:
            self.raise_error('max_whole_digits', max_whole_digits=self.max_whole_digits)
        return value

    def quantize(self, value):
        """
        将十进制值量化为配置的精度。
        """
        if self.decimal_places is None:
            return value

        context = decimal.getcontext().copy()
        if self.max_digits is not None:
            context.prec = self.max_digits
        return value.quantize(
            decimal.Decimal('.1') ** self.decimal_places,
            rounding=self.rounding,
            context=context
        )


class BooleanField(Field):
    """布尔值类型"""
    _doc_type = 'boolean'

    default_error_messages = {
        'invalid': 'Must be a valid boolean.',
    }
    TRUE_VALUES = {
        't', 'T',
        'y', 'Y', 'yes', 'YES',
        'true', 'True', 'TRUE',
        'on', 'On', 'ON',
        '1', 1,
        True
    }
    FALSE_VALUES = {
        'f', 'F',
        'n', 'N', 'no', 'NO',
        'false', 'False', 'FALSE',
        'off', 'Off', 'OFF',
        '0', 0, 0.0,
        False
    }
    NULL_VALUES = {'null', 'Null', 'NULL', '', None}

    async def external_to_internal(self, data: Any) -> Any:
        try:
            if data in self.TRUE_VALUES:
                return True
            elif data in self.FALSE_VALUES:
                return False
            elif data in self.NULL_VALUES and self.allow_null:
                return None
        except TypeError:
            self.raise_error('invalid')

    async def internal_to_external(self, data: Any) -> Any:
        if data in self.TRUE_VALUES:
            return True
        elif data in self.FALSE_VALUES:
            return False
        if data in self.NULL_VALUES and self.allow_null:
            return None
        return bool(data)


class DateTimeField(Field):
    """日期时间类型"""
    _doc_type = 'string'
    _doc_format = 'date-time'

    default_error_messages = {
        'invalid': 'Wrong type, should be datetime or string',
        'format': 'Datetime has wrong format. Use one of these formats instead: {format}.',
        'overflow': 'Datetime value out of range.'
    }

    def __init__(self, output_format='%Y-%m-%d %H:%M:%S', input_format='%Y-%m-%d %H:%M:%S',
                 set_timezone: timezone = None, *args, **kwargs):
        self.output_format = output_format
        self.input_format = input_format
        if set_timezone is not None:
            self.set_timezone = set_timezone
        else:
            self.set_timezone = self.get_default_timezone()
        super(DateTimeField, self).__init__(*args, **kwargs)

    def get_default_timezone(self):
        """设置默认时区为北京时间"""
        return timezone(timedelta(hours=8))

    def enforce_timezone(self, value):
        """强制设置一个时区"""

        try:
            return value.astimezone(self.set_timezone)
        except OverflowError:
            self.raise_error('overflow')

    async def external_to_internal(self, data: Any) -> Any:
        if not isinstance(data, (str, datetime)):
            self.raise_error('invalid')
        if isinstance(data, str):
            try:
                data = datetime.strptime(data, self.input_format)
            except (ValueError, TypeError):
                self.raise_error('format', format=self.input_format)
        data = self.enforce_timezone(data)
        return data

    async def internal_to_external(self, data: Any) -> Any:
        if not data:
            return None
        if isinstance(data, str):
            return data
        data = datetime.strptime(data, self.input_format)
        return data.strftime(self.output_format)


class DateField(Field):
    """日期字段"""
    _doc_type = 'string'
    _doc_format = 'date-time'

    default_error_messages = {
        'invalid': 'Wrong type, should be date or string',
        'format': 'Datetime has wrong format. Use one of these formats instead: {format}.',
    }

    def __init__(self, output_format='%Y-%m-%d', input_format='%Y-%m-%d', *args, **kwargs):
        self.output_format = output_format
        self.input_format = input_format
        super(DateField, self).__init__(*args, **kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        if not isinstance(data, (str, date)):
            self.raise_error('invalid')
        if isinstance(data, str):
            try:
                data = datetime.strptime(data, self.input_format).date()
            except (ValueError, TypeError):
                self.raise_error('format', format=self.input_format)
        return data

    async def internal_to_external(self, data: Any) -> Any:
        if not data:
            return None
        if isinstance(data, str):
            return data
        data = datetime.strptime(data, self.input_format).date()
        return data.strftime(self.output_format)


class TimeField(Field):
    """时间字段"""

    default_error_messages = {
        'invalid': 'Wrong type, should be datetime.time',
        'format': 'Time has wrong format. Use one of these formats instead: {format}.',

    }

    def __init__(self, output_format='%H:%M:%S', input_format='%H:%M:%S', *args, **kwargs):
        self.output_format = output_format
        self.input_format = input_format
        super(TimeField, self).__init__(*args, **kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        if not isinstance(data, (str, time)):
            self.raise_error('invalid')
        if isinstance(data, time):
            return data
        try:
            data = datetime.strptime(data, self.input_format).time()
        except (ValueError, TypeError):
            self.raise_error('format', format=self.input_format)
        return data

    async def internal_to_external(self, data: Any) -> Any:
        if not data:
            return None
        if isinstance(data, str):
            return data
        assert not isinstance(data, datetime), (
            'Expected a `time`, but got a `datetime`. Refusing to coerce, '
            'as this may mean losing timezone information. Use a custom '
            'read-only field and deal with timezone issues explicitly.'
        )
        return datetime.strptime(data, self.input_format)


class ChoiceField(Field):
    """限定可选的字段"""
    default_error_messages = {
        'invalid_choice': '"{input}" is not a valid choice.',
    }

    def __init__(self, choices, *args, **kwargs):
        """
        :param choices: (('key','value'),('key','value'),)
        :param args:
        :param kwargs:
        """
        self.choices = choices
        super(ChoiceField, self).__init__(*args, **kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        if self.check_key_choices(data):
            return data
        self.raise_error('invalid_choice', input=data)

    async def internal_to_external(self, data: Any) -> Any:
        return self.choices_get_value_by_key(data)

    def choices_get_value_by_key(self, key):
        """得到字符串"""
        if self.check_key_choices(key):
            choices_dict = self.get_choices()
            value = choices_dict[key]
            return value
        return key

    def check_key_choices(self, key):
        choices_dict = self.get_choices()
        return key in choices_dict

    def get_choices(self) -> dict:
        choices = {key: value for key, value in self.choices}
        return choices


class EnumChoiceField(Field):
    """枚举类型字段"""

    def __init__(self, enum_type, value_type, *args, **kwargs):
        """
        :param enum_type: 枚举类
        :param value_type: 枚举类
        :param value_map: 值的映射对象
        :param args:
        :param kwargs:
        """
        self.enum_type = enum_type
        self.value_type = value_type
        super(EnumChoiceField, self).__init__(*args, **kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        return self.enum_type(self.value_type(data)) if data is not None else None

    async def internal_to_external(self, data: Any) -> Any:
        if isinstance(data, Enum):
            return self.value_type(data.value)
        if isinstance(data, self.value_type):
            return self.value_type(self.enum_type(data).value)
        return self.value_type(data)


class ListField(Field):
    _doc_type = 'array'
    _doc_format = None
    child = None
    initial = []
    default_error_messages = {
        'not_a_list': 'Expected a list of items but got type "{input_type}".',
        'empty': 'This list may not be empty.',
        'min_length': 'Ensure this field has at least {min_length} elements.',
        'max_length': 'Ensure this field has no more than {max_length} elements.'
    }

    def __init__(self, **kwargs):
        self.child = kwargs.pop('child', copy.deepcopy(self.child))
        self.allow_empty = kwargs.pop('allow_empty', True)
        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)

        assert not inspect.isclass(self.child), '`child` has not been instantiated.'
        assert self.child.source is None, (
            "The `source` argument is not meaningful when applied to a `child=` field. "
            "Remove `source=` from the field declaration."
        )

        super().__init__(**kwargs)
        self.child.bind(field_name='', parent=self)
        if self.max_length is not None:
            message = {'max_length': 'Ensure this field has no more than {max_length} elements.'}
            self.validators.append(MaxLengthValidator(self.max_length, message=message))
        if self.min_length is not None:
            message = {'min_length': 'Ensure this field has at least {min_length} elements.'}
            self.validators.append(MinLengthValidator(self.min_length, message=message))

    def _doc_properties(self):
        return {
            "title": '状态码',
            "type": 'array',
            "items": self.child._doc_properties()
        }

    async def external_to_internal(self, data: Any) -> Any:
        """
        List of dicts of native values <- List of dicts of primitive datatypes.
        """
        if isinstance(data, (str, Mapping)) or not hasattr(data, '__iter__'):
            self.raise_error('not_a_list', input_type=type(data).__name__)
        if not self.allow_empty and len(data) == 0:
            self.raise_error('empty')
        return await self.run_child_validation(data)

    async def internal_to_external(self, data: Any) -> Any:
        """
        List of object instances -> List of dicts of primitive datatypes.
        """
        return [await self.child.internal_to_external(item) if item is not None else None for item in data]

    async def run_child_validation(self, data):
        result = []
        errors = OrderedDict()

        for idx, item in enumerate(data):
            try:
                result.append(await self.child.run_validation(item))
            except ValidationException as e:
                errors[idx] = e.error_detail

        if not errors:
            return result
        raise ValidationException(errors)


class RelatedField(Field):
    queryset = None

    def __init__(self, **kwargs):
        self.queryset = kwargs.pop('queryset', self.queryset)
        super(RelatedField, self).__init__(**kwargs)

    async def get_queryset(self):
        return self.queryset


class PrimaryKeyRelatedField(RelatedField):
    default_error_messages = {
        'invalid': 'Invalid value.',
        'not_exist': 'This value `{value}` is not valid',
    }

    async def external_to_internal(self, data: Any) -> Any:
        if self.allow_null and data in ('', None):
            return None
        queryset = await self.get_queryset()
        try:
            return await queryset.get(pk=data)
        except DoesNotExist:
            raise self.raise_error('not_exist', value=data)
        except (TypeError, ValueError):
            self.raise_error('invalid')

    async def internal_to_external(self, data: Any) -> Any:
        return data.pk


class SlugRelatedField(RelatedField):
    """
    A read-write field that represents the target of the relationship
    by a unique 'slug' attribute.
    """
    default_error_messages = {
        'invalid': 'Invalid value.',
        'does_not_exist': 'Object with {slug_name}={value} does not exist.',
    }

    def __init__(self, slug_field=None, **kwargs):
        assert slug_field is not None, 'The `slug_field` argument is required.'
        self.slug_field = slug_field
        super().__init__(**kwargs)

    async def external_to_internal(self, data):
        queryset = await self.get_queryset()
        try:
            return await queryset.get(**{self.slug_field: data})
        except DoesNotExist:
            self.raise_error('does_not_exist', slug_name=self.slug_field, value=data)
        except (TypeError, ValueError):
            self.raise_error('invalid')

    async def internal_to_external(self, data):
        return getattr(data, self.slug_field)


class ManyRelatedField(RelatedField):
    default_error_messages = {
        'invalid': 'Invalid value.',
        'not_exist': 'This value `{value}` is not valid',
    }

    def __init__(self, child_relation, **kwargs):
        self.child_relation = child_relation
        super(ManyRelatedField, self).__init__(**kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        return [
            await self.child_relation.external_to_internal(item)
            for item in data
        ]

    async def internal_to_external(self, data: Any) -> Any:
        return [
            await self.child_relation.internal_to_external(value)
            for value in data
        ]

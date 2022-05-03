"""
@Author: WangYuXiang
@E-mile: Hill@3io.cc
@CreateTime: 2021/1/20 13:20
@DependencyLibrary:
@MainFunction：
@FileDoc:
    fields.py
    文件说明
"""
import copy
import decimal
import re
from datetime import timezone, timedelta, datetime, date, time
from enum import Enum
from typing import Any, List, Mapping

from tortoise.exceptions import DoesNotExist

from srf.exceptions import ValidationException
from srf.openapi import PropItem
from srf.utils import is_callable, run_awaitable, run_awaitable_val
from srf.validators import (
    MaxLengthValidator, MinLengthValidator, MaxValueValidator, MinValueValidator
)

REGEX_TYPE = type(re.compile(''))

__all__ = ('empty', 'SkipField', 'Field', 'CharField', 'IntegerField', 'FloatField', 'DecimalField', 'BooleanField',
           'DateTimeField', 'DateField', 'TimeField', 'ChoiceField', 'EnumChoiceField', 'SerializerMethodField')


class empty:
    """
    此类代表空，因为有些字段可以为 None
    所以需要一个可以替代 None 代表空变量
    """
    pass


class SkipField(Exception):
    pass


NOT_RAED_ONLY_AND_WRITE_ONLY = 'read_only 和 write_only 不能同时为True, 只能二选一'
NOT_RAED_ONLY_REQUIRED_ONLY = 'read_only 为 True 时 required 不能为True , 只能二选一'


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

    def __init__(self, read_only=False, write_only=False, required=False, allow_null=False,
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
            '{cls}类的 .external_to_internal 方法必须重写'.format(cls=self.__class__.__name__, )
        )

    async def internal_to_external(self, data: Any) -> Any:
        """对数据进行序列化转换并返回"""
        raise NotImplementedError(
            '{cls}类的 .external_to_internal 方法必须重写'.format(cls=self.__class__.__name__, )
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
            msg = "在 {class_name} 类的 error_messages " \
                  "属性中未能找到 Key 为 {key} 的错误描述".format(class_name=class_name, key=_key)
            raise AssertionError(msg)
        message_string = msg.format(**kwargs)
        raise ValidationException(message_string, code=_key)

    def __str__(self):
        return super(Field, self).__str__() + self.field_name


class CharField(Field):
    """字符字段"""
    default_error_messages = {
        'invalid': '出现错误的数据类型，仅支持整字符类型',
        'max_length': '最长支持{max_length}个字符',
        'min_length': '至少要有{min_length}个字符',
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
        'invalid': '出现错误的数据类型，仅支持整数类型',
        'max_value': '仅支持小于{max_value}的整数',
        'min_value': '仅支持大于{min_value}的整数',
        'max_string_length': '仅支持转换长度小于{max_string_length}的整数字符串',
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
            self.raise_error('max_string_length', max_string_length=self.MAX_STRING_LENGTH)
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
        'invalid': '出现错误的数据类型{data_type}，仅支持浮点类型',
        'max_value': '仅支持小于{max_value}浮点',
        'min_value': '仅支持大于{min_value}浮点',
        'max_string_length': '仅支持转换长度小于{max_string_length}的浮点字符串',
    }
    MAX_STRING_LENGTH = 1000

    async def external_to_internal(self, data: Any):
        if isinstance(data, bool):
            self.raise_error('invalid', data_type=type(data).__name__)
        if isinstance(data, str) and len(data) > self.MAX_STRING_LENGTH:
            self.raise_error('max_string_length', max_string_length=self.MAX_STRING_LENGTH)
        try:
            return float(data)
        except (TypeError, ValueError):
            self.raise_error('invalid', data_type=type(data).__name__)

    async def internal_to_external(self, data: Any):
        return float(data)


class DecimalField(Field):
    """十进制类型"""
    _doc_type = 'number'
    _doc_format = 'float'

    default_error_messages = {
        'invalid': '出现错误的数据类型，仅支持Decimal十进制类型',
        'max_value': '仅支持小于{max_value}Decimal十进制类型',
        'min_value': '仅支持大于{min_value}Decimal十进制类型',
        'max_string_length': '仅支持转换长度小于{max_string_length}的Decimal十进制字符串',
        'max_digits': '确保总数不超过{max_digits}个数字。',
        'max_decimal_places': '确保不超过{max_decimal_places}个小数位。',
        'max_whole_digits': '确保小数点前的位数不超过{max_whole_digits}个。',
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
            self.raise_error('max_string_length', max_string_length=self.MAX_STRING_LENGTH)
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
        'invalid': '出现错误的数据类型，{value}不是有效的布尔值',
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
            self.raise_error('invalid', value=data)

    async def internal_to_external(self, data: Any) -> Any:
        if data in self.TRUE_VALUES:
            return True
        elif data in self.FALSE_VALUES:
            return False
        if data in self.NULL_VALUES and self.allow_null:
            return None
        return bool(data)


class DateField(Field):
    """日期字段"""
    _doc_type = 'string'
    _doc_format = 'date-time'

    default_error_messages = {
        'invalid': '出现错误的数据类型，{value}不是有效的日期时间类型',
        'datetime': '需要的是日期格式而不是日期时间格式',
    }

    def __init__(self, output_format='%Y-%m-%d', input_format='%Y-%m-%d', *args, **kwargs):
        self.output_format = output_format
        self.input_format = input_format
        super(DateField, self).__init__(*args, **kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        if isinstance(data, str):
            try:
                data = datetime.strptime(data, self.input_format).date()
            except (ValueError, TypeError):
                self.raise_error('invalid', value=data)
        if isinstance(data, datetime):
            self.raise_error('datetime')
        if isinstance(data, date):
            return data
        self.raise_error('invalid', value=data)

    async def internal_to_external(self, data: Any) -> Any:
        if isinstance(data, str):
            try:
                data = datetime.strptime(data, self.input_format).date()
            except (ValueError, TypeError):
                self.raise_error('invalid', value=data)
        if isinstance(data, date):
            return data.strftime(self.output_format)
        self.raise_error('invalid', value=data)


class DateTimeField(Field):
    """日期时间类型"""
    _doc_type = 'string'
    _doc_format = 'date-time'

    default_error_messages = {
        'invalid': '错误的数据类型{data_type}, 不能转换为字符格式',
        'convert': '日期转换异常，请确认日期格式符合 %Y-%m-%d %H:%M:%S 规则',
        'date': '需要的是日期时间格式而不是日期格式',
        'overflow': '时间超出范围'
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
        return value.astimezone(self.set_timezone)

    async def external_to_internal(self, data: Any) -> Any:
        if not isinstance(data, (str, date, datetime)):
            self.raise_error('convert')
        if type(data) == date:
            self.raise_error('date')
        if isinstance(data, str):
            try:
                data = datetime.strptime(data, self.input_format)
            except (ValueError, TypeError):
                self.raise_error('convert')
        if type(data) == datetime:
            data = self.enforce_timezone(data)
        return data

    async def internal_to_external(self, data: Any) -> Any:
        if isinstance(data, str):
            try:
                data = datetime.strptime(data, self.input_format)
            except (ValueError, TypeError):
                self.raise_error('convert')
        if isinstance(data, datetime):
            return data.strftime(self.output_format)
        self.raise_error('invalid', data_type=type(data).__name__)


class TimeField(Field):
    """时间字段"""

    default_error_messages = {
        'invalid': '出现错误的数据类型，{value}不是有效的日期时间类型',
        'format': '时间格式错误，需要格式为 %H:%M:%S ',
        'date': '需要的是时间格式而不是日期格式',
        'datetime': '需要的是时间格式而不是日期时间格式',
    }

    def __init__(self, output_format='%H:%M:%S', input_format='%H:%M:%S', *args, **kwargs):
        self.output_format = output_format
        self.input_format = input_format
        super(TimeField, self).__init__(*args, **kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        if isinstance(data, str):
            try:
                data = datetime.strptime(data, self.input_format).time()
                return data
            except (ValueError, TypeError):
                self.raise_error('format')
        if isinstance(data, datetime):
            self.raise_error('datetime')
        if isinstance(data, time):
            return data
        if isinstance(data, date):
            self.raise_error('date')
        self.raise_error('invalid', value=type(data))

    async def internal_to_external(self, data: Any) -> Any:
        if isinstance(data, str):
            try:
                data = datetime.strptime(data, self.input_format).time()
            except (ValueError, TypeError):
                self.raise_error('format')
        if isinstance(data, datetime):
            data = data.time()
        if isinstance(data, time):
            return data.strftime(self.output_format)
        self.raise_error('invalid', value=data)


class ChoiceField(Field):
    """限定可选的字段"""
    default_error_messages = {
        'invalid': '出现错误的数据类型，{value}不是有效的日期时间类型',
        'key': '错误选项{key}',
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
        return self.choices_get_value_by_key(data)

    async def internal_to_external(self, data: Any) -> Any:
        return self.choices_get_value_by_key(data)

    def choices_get_value_by_key(self, key):
        """得到字符串"""
        if self.check_key_choices(key):
            choices_dict = self.get_choices()
            value = choices_dict[key]
            return value
        self.raise_error('key', key=key)

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


class SerializerMethodField(Field):
    """
    一个只读字段，可通过在父序列化器类。调用的方法将具有以下形式
    “ get_ {field_name}”，并且应采用单个参数，即
    对象被序列化。
    For example:

    class ExampleSerializer(self):
        extra_info = SerializerMethodField()

        def get_extra_info(self, obj):
            return ...  # Calculate some data to return.
    """

    def __init__(self, method_name=None, **kwargs):
        self.method_name = method_name
        kwargs['source'] = '*'
        kwargs['read_only'] = True
        if kwargs.get('required'):
            assert 'SerializerMethodField 为只读字段，不能反序列化'

        super().__init__(**kwargs)

    def bind(self, field_name, parent):
        # The method name defaults to `get_{field_name}`.
        if self.method_name is None:
            self.method_name = 'get_{field_name}'.format(field_name=field_name)

        super().bind(field_name, parent)

    async def internal_to_external(self, data: Any) -> Any:
        method = getattr(self.parent, self.method_name)
        return await run_awaitable(method, data)

    def external_to_internal(self, data: Any) -> Any:
        raise ValidationException('SerializerMethodField 不支持反序列化')

    def _doc_properties(self):
        return None

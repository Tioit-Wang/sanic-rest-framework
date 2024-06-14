"""
@Author: TioitWang
@E-mile: me@tioit.cc
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
from datetime import date, datetime, time, timezone
from enum import Enum
from typing import Any, Mapping, Optional

from sanic.log import logger
from tortoise.exceptions import DoesNotExist

from settings import TIMEZONE
from rest_framework.exceptions import ValidationException
from rest_framework.openapi3.types import Array, Boolean, Date, DateTime, Float, Integer, Schema, String, Time
from rest_framework.utils import run_awaitable, run_awaitable_val
from rest_framework.validators import BaseValidator, MaxLengthValidator, MaxValueValidator, MinLengthValidator, MinValueValidator

REGEX_TYPE = type(re.compile(''))
NOT_READ_ONLY_AND_WRITE_ONLY = 'May not set both `read_only` and `write_only`'
NOT_READ_ONLY_REQUIRED_ONLY = 'May not set both `read_only` and `required`'

__all__ = (
    'empty',
    'SkipField',
    'Field',
    'CharField',
    'IntegerField',
    'FloatField',
    'DecimalField',
    'BooleanField',
    'DateTimeField',
    'DateField',
    'TimeField',
    'ChoiceField',
    'EnumChoiceField',
    'ListField',
    'SerializerMethodField',
    'RelatedField',
    'PrimaryKeyRelatedField',
    'ManyRelatedField',
    'SlugRelatedField',
)


async def get_attribute(instance, attrs):
    """
    Similar to Python's built in `getattr(instance, attr)`,
    but takes a list of nested attributes, instead of a single attribute.

    Also accepts either attribute lookup on objects or dictionary lookups.
    """
    for attr in attrs:
        try:
            if isinstance(instance, Mapping):
                instance = instance[attr]
            else:
                instance = getattr(instance, attr)
        except DoesNotExist:
            return None
        if callable(instance):
            try:
                instance = await run_awaitable(instance)
            except (AttributeError, KeyError) as exc:
                # If we raised an Attribute or KeyError here it'd get treated
                # as an omitted field in `Field.get_attribute()`. Instead we
                # raise a ValueError to ensure the exception is not masked.
                raise ValueError('Exception raised in callable attribute "{}"; original exception was: {}'.format(attr, exc))

    return instance


class empty:
    """
    此类代表空，因为有些字段可以为 None
    所以需要一个可以替代 None 代表空变量
    """

    pass


class SkipField(Exception):
    pass


class Field:
    """
    Represents a generic field with various validation and formatting options.

    Class Variables:
        _sort_counter (int): A counter to keep the sort order of fields.
        base_error_messages (dict): Default base error messages for the field.
        default_error_messages (Optional[dict]): Default error messages that can be overridden.
        default_validators (Optional[list]): Default validators that can be overridden.

    Attributes:
        read_only (bool): If True, the field is read-only.
        write_only (bool): If True, the field is write-only.
        required (bool): If True, the field is required.
        allow_null (bool): If True, the field can be null.
        default (Any): Default value for the field.
        source (Optional[str]): Source attribute path of the field.
        validators (list): List of validators for the field.
        error_messages (dict): Error messages for the field.
        description (Optional[str]): Description for the field.
        field_name (Optional[str]): Name of the field.
        parent (Optional[Any]): Parent of the field.

    Methods:
        bind(field_name, parent): Binds the field to a field_name and parent.
        collect_error_messages(error_messages): Collects and returns the merged error messages.
        collect_validator_list(validators): Collects and returns the merged validators.
        is_partial(root=None): Checks if the field or its root is in partial mode.
        external_to_internal(data): Converts external data to internal representation.
        internal_to_external(data): Converts internal data to external representation.
        get_external_value(data): Gets the external value from the data mapping.
        get_internal_value(instance): Gets the internal value from the instance.
        run_validators(data): Runs all validators on the data.
        get_default(): Gets the default value for the field.
        validate_empty_values(data): Validates empty values.
        run_validation(data): Runs complete validation including external to internal conversion.
        root: Property that returns the root field.
        context: Property that returns the context of the root field.
        raise_error(error_key, kwargs): Raises a validation error.
        _default_clsattr_to_oapiattr(): Converts class attributes to OpenAPI attributes.
        to_openapi(): Converts the field to an OpenAPI schema.
    """

    _sort_counter = 0
    base_error_messages = {
        'required': 'This field is required and must be included upon submission.',
        'null': 'This field cannot be null.',
    }
    default_error_messages = None
    default_validators = None

    def __init__(
        self,
        read_only=False,
        write_only=False,
        required=None,
        allow_null=False,
        default=empty,
        source=None,
        validators=None,
        error_messages=None,
        description=None,
    ):
        """
        Initializes a new instance of the Field class.

        Args:
            read_only (bool): If True, the field is read-only. Cannot be used with write_only.
            write_only (bool): If True, the field is write-only. Cannot be used with read_only.
            required (Optional[bool]): If True, the field is required and must be included upon submission.
            allow_null (bool): If True, the field can be null. Only effective during deserialization.
            default (Any): The default value.
            source (Optional[str]): The field source. Only effective during serialization.
            validators (Optional[list]): List of validators for the field.
            error_messages (Optional[dict]): Error messages for the field.
            description (Optional[str]): Description for the field.
        """
        assert not (read_only and write_only), NOT_READ_ONLY_AND_WRITE_ONLY
        assert not (read_only and required), NOT_READ_ONLY_REQUIRED_ONLY

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
        self.description = description

        self.validators = self.collect_validator_list([validators, self.default_validators])
        self.error_messages = self.collect_error_messages([self.base_error_messages, self.default_error_messages, error_messages])

        self.field_name = None
        self.parent = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        instance._args = args
        instance._kwargs = kwargs
        return instance

    def __deepcopy__(self, memo):
        """
        Clone the field using the parameters that were initially used to create it,
        rather than copying the full state.
        """
        args = [copy.deepcopy(item) if not isinstance(item, REGEX_TYPE) else item for item in self._args]
        kwargs = {
            key: (copy.deepcopy(value, memo) if (key not in ('validators', 'regex')) else value) for key, value in self._kwargs.items()
        }
        return self.__class__(*args, **kwargs)

    def __str__(self):
        return super(Field, self).__str__() + self.field_name

    def bind(self, field_name, parent):
        """
        Bind the field to a parent instance.
        """
        self.field_name = field_name
        self.parent = parent

        if self.source is None:
            self.source = self.field_name

        if self.source == '*':
            self.source_attrs = []
        else:
            self.source_attrs = self.source.split('.')

    def collect_error_messages(self, error_messages: list[dict]) -> dict:
        """
        Collect error messages into a single dictionary.
        """
        cur_error_messages = {}
        for error_message in error_messages:
            if error_message is not None:
                cur_error_messages.update(error_message)
        return cur_error_messages

    def collect_validator_list(self, validators: list[BaseValidator]) -> list:
        """
        Collect all validators into a single list.
        """
        all_validators = []
        for validator_list in validators:
            if validator_list is not None:
                for validator in validator_list:
                    if validator not in all_validators:
                        all_validators.append(validator)
        return all_validators

    def is_partial(self, root=None) -> bool:
        """
        Check if the request is a partial update.
        """
        if root is None:
            root = self.root
        return getattr(root, 'partial', False)

    async def external_to_internal(self, data: Any) -> Any:
        raise NotImplementedError('subclasses of {cls} must provide an external_to_internal() method'.format(cls=self.__class__.__name__))

    async def internal_to_external(self, data: Any) -> Any:
        raise NotImplementedError(
            'subclasses of `{cls}` must provide an internal_to_external() method'.format(cls=self.__class__.__name__)
        )

    async def get_external_value(self, data: Mapping) -> Any:
        """
        Retrieve a value from the external source data for input validation.
        """
        if not isinstance(data, Mapping):
            raise ValidationException(
                "Invalid data type for field `{field_name}`. Only dictionary type is supported.".format(field_name=self.field_name)
            )

        # source 不作用于 deserialize
        if self.field_name not in data:
            if self.is_partial():
                return empty
            if self.required:
                if self.default is not empty and not self.is_partial():
                    return self.get_default()
                self.raise_error('required')
            return self.get_default()

        value = await get_attribute(data, [self.field_name])
        return value

    async def get_internal_value(self, instance: Any) -> Any:
        """
        Retrieve a value from the internal source data for output.
        """
        for attr in self.source_attrs:
            if instance is None:
                return None

            try:
                if isinstance(instance, Mapping):
                    instance = instance[attr]
                else:
                    instance = getattr(instance, attr)
                    if callable(instance):
                        instance = await run_awaitable(instance)
                    else:
                        instance = await run_awaitable_val(instance)
            except (KeyError, AttributeError, DoesNotExist):
                if self.default is not empty:
                    return self.get_default()
                if self.required:
                    self.raise_error('required')
                return None
        return instance

    def run_validators(self, data) -> None:
        """
        Run validators on input data.
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
        """
        Get the default value
        """
        if self.default is empty or getattr(self.root, 'partial', False):
            raise SkipField()
        if callable(self.default):
            return self.default()
        return self.default

    def validate_empty_values(self, data):
        """
        Check if the data is empty and handle it accordingly.
        """
        if self.read_only:
            return True, self.get_default()
        if data is empty:
            if self.is_partial():
                raise SkipField()
            if self.required:
                if self.default is not empty and not self.is_partial():
                    return False, self.get_default()
                self.raise_error('required')
            return True, self.get_default()

        if data is None:
            if not self.allow_null:
                self.raise_error('null')
            elif self.source == '*':
                return False, None
            return True, None
        return False, data

    async def run_validation(self, data):
        """
        Execute validation on the data.
        """
        is_empty_value, data = self.validate_empty_values(data)
        if is_empty_value:
            return data
        value = await self.external_to_internal(data)
        self.run_validators(value)
        return value

    @property
    def root(self):
        """
        Get the top-level parent of the field.
        """
        root = self
        while root.parent is not None:
            root = root.parent
        return root

    @property
    def context(self):
        """
        Return the context passed to the root serializer.
        """
        return getattr(self.root, '_context', {})

    def raise_error(self, error_key, **kwargs):
        """
        Raise an error based on registered error messages.
        """
        try:
            msg = self.error_messages[error_key]
        except KeyError:
            class_name = self.__class__.__name__
            msg = (
                'ValidationError raised by `{class_name}`, but error key `{key}` does '
                'not exist in the `error_messages` dictionary.'.format(class_name=class_name, key=error_key)
            )
            raise AssertionError(msg)
        message_string = msg.format(**kwargs)
        raise ValidationException(message_string, code=error_key)

    def _default_clsattr_to_oapiattr(self) -> dict:
        keywords = {}
        if self.description is not None:
            keywords['description'] = self.description
        if self.default is not empty:
            keywords['default'] = self.get_default()
        if self.allow_null is not None:
            keywords['nullable'] = self.allow_null
        if self.required is not None:
            keywords['required'] = self.required
        return keywords

    def to_openapi(self) -> Schema:
        """
        Generate an OpenAPI 3.0 item JSON representation for the field.
        """
        raise NotImplementedError('subclasses of {cls} must provide a to_openapi() method'.format(cls=self.__class__.__name__))


class CharField(Field):
    """
    Character field for handling string data.

    Attributes:
        max_length (int): Maximum number of characters allowed.
        min_length (int): Minimum number of characters required.
        trim_whitespace (bool): Indicates whether to trim whitespace.
        default_error_messages (dict): Custom error messages for validation.
    """

    default_error_messages = {
        'invalid': 'Must be a valid string.',
        'max_length': 'Ensure this field has no more than {max_length} characters.',
        'min_length': 'The value must contain at least {min_length} characters.',
    }

    def __init__(self, *args, **kwargs):
        """
        Initialize CharField with optional max_length, min_length, and trim_whitespace.

        Args:
            max_length (int, optional): Maximum number of characters allowed.
            min_length (int, optional): Minimum number of characters required.
            trim_whitespace (bool, optional): Indicates whether to trim whitespace.
        """
        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)
        self.trim_whitespace = kwargs.pop('trim_whitespace', True)
        super(CharField, self).__init__(*args, **kwargs)
        if self.max_length is not None:
            self.validators.append(
                MaxLengthValidator(max_length=self.max_length, error_messages={'max_length': self.error_messages['max_length']})
            )
        if self.min_length is not None:
            self.validators.append(
                MinLengthValidator(min_length=self.min_length, error_messages={'min_length': self.error_messages['min_length']})
            )

    async def external_to_internal(self, data: Any) -> Any:
        if not isinstance(data, (str, int, float)):
            self.raise_error('invalid')
        value = str(data)
        return value.strip() if self.trim_whitespace else value

    async def internal_to_external(self, data: Any) -> Any:
        return str(data)

    def to_openapi(self) -> Schema:
        keywords = self._default_clsattr_to_oapiattr()

        if self.max_length is not None:
            keywords['maxLength'] = self.max_length
        if self.min_length is not None:
            keywords['minLength'] = self.min_length

        return String(**keywords)


class IntegerField(Field):
    """
    Integer field for handling integer data.

    Attributes:
        max_value (int): Maximum allowed value.
        min_value (int): Minimum allowed value.
        default_error_messages (dict): Custom error messages for validation.
        re_decimal (re.Pattern): Regular expression to match decimal values.
        MAX_STRING_LENGTH (int): Maximum length of string representation of the value.
    """

    default_error_messages = {
        'invalid': 'Must be a valid integer.',
        'max_value': 'Ensure this value is less than or equal to {max_value}',
        'min_value': 'Ensure this value is greater than or equal to {min_value}',
        'max_string_length': 'String value too large.',
    }
    re_decimal = re.compile(r'\.0*\s*$')
    MAX_STRING_LENGTH = 1000

    def __init__(self, *args, **kwargs):
        """
        Initialize IntegerField with optional max_value and min_value.

        Args:
            max_value (int, optional): Maximum allowed value.
            min_value (int, optional): Minimum allowed value.
        """
        self.max_value = kwargs.pop('max_value', None)
        self.min_value = kwargs.pop('min_value', None)
        super().__init__(*args, **kwargs)
        if self.max_value is not None:
            self.validators.append(
                MaxValueValidator(max_value=self.max_value, error_messages={'max_value': self.error_messages['max_value']})
            )
        if self.min_value is not None:
            self.validators.append(
                MinValueValidator(min_value=self.min_value, error_messages={'min_value': self.error_messages['min_value']})
            )

    async def external_to_internal(self, data: Any) -> Any:
        if isinstance(data, str) and len(data) > self.MAX_STRING_LENGTH:
            self.raise_error('max_string_length')
        try:
            data = int(self.re_decimal.sub('', str(data)))
        except (ValueError, TypeError):
            self.raise_error('invalid')
        return data

    async def internal_to_external(self, data: Any) -> Any:

        return int(data)

    def to_openapi(self) -> Schema:
        keywords = self._default_clsattr_to_oapiattr()
        if self.max_value is not None:
            keywords['maximum'] = self.max_value
        if self.min_value is not None:
            keywords['minimum'] = self.min_value

        return Integer(**keywords)


class FloatField(IntegerField):
    """
    Float field for handling float data.

    Attributes:
        _documentation_type (str): The OpenAPI type for the field.
        _documentation_format (str): The OpenAPI format for the field.
        default_error_messages (dict): Custom error messages for validation.
        MAX_STRING_LENGTH (int): Maximum length of string representation of the value.
    """

    default_error_messages = {
        'invalid': 'Must be a valid float.',
        'max_value': 'Ensure this value is less than or equal to {max_value}',
        'min_value': 'Ensure this value is greater than or equal to {min_value}',
        'max_string_length': 'String value too large.',
    }
    MAX_STRING_LENGTH = 1000

    async def external_to_internal(self, data: Any) -> Any:
        if isinstance(data, str) and len(data) > self.MAX_STRING_LENGTH:
            self.raise_error('max_string_length')
        try:
            return float(data)
        except (TypeError, ValueError):
            self.raise_error('invalid')

    async def internal_to_external(self, data: Any) -> Any:
        return float(data)

    def to_openapi(self) -> Schema:
        keywords = self._default_clsattr_to_oapiattr()
        if self.max_value is not None:
            keywords['maximum'] = self.max_value
        if self.min_value is not None:
            keywords['minimum'] = self.min_value

        return Float(**keywords)


class DecimalField(Field):
    """
    Decimal field for handling decimal data.

    Attributes:
        max_digits (int): Maximum number of digits allowed in the number.
        decimal_places (int): Maximum number of decimal places allowed.
        coerce_to_string (bool): Indicates whether to coerce the value to a string.
        max_value (decimal.Decimal): Maximum allowed value.
        min_value (decimal.Decimal): Minimum allowed value.
        rounding (str): Rounding strategy to use.
        max_whole_digits (int): Maximum number of digits before the decimal point.
        MAX_STRING_LENGTH (int): Maximum length of string representation of the value.
        default_error_messages (dict): Custom error messages for validation.
    """

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

    def __init__(
        self,
        max_digits,
        decimal_places,
        coerce_to_string=False,
        max_value: Optional[decimal.Decimal] = None,
        min_value: Optional[decimal.Decimal] = None,
        rounding=None,
        *args,
        **kwargs
    ):
        """
        Initialize DecimalField with required max_digits and decimal_places, and optional coerce_to_string, max_value, min_value, and rounding.

        Args:
            max_digits (int): Maximum number of digits allowed in the number.
            decimal_places (int): Maximum number of decimal places allowed.
            coerce_to_string (bool, optional): Indicates whether to coerce the value to a string. Defaults to False.
            max_value (decimal.Decimal, optional): Maximum allowed value. Defaults to None.
            min_value (decimal.Decimal, optional): Minimum allowed value. Defaults to None.
            rounding (str, optional): Rounding strategy to use. Defaults to None.
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
            self.validators.append(
                MaxValueValidator(max_value=self.max_value, error_messages={'max_value': self.error_messages['max_value']})
            )
        if self.min_value is not None:
            self.validators.append(
                MinValueValidator(min_value=self.min_value, error_messages={'min_value': self.error_messages['min_value']})
            )

    async def external_to_internal(self, data: Any) -> Any:
        data = str(data).strip()

        if len(data) > self.MAX_STRING_LENGTH:
            self.raise_error('max_string_length')
        try:
            data = decimal.Decimal(data)
        except decimal.DecimalException:
            self.raise_error('invalid')

        if data.is_nan():
            self.raise_error('invalid')

        # Check for infinity and negative infinity.
        if data in (decimal.Decimal('Inf'), decimal.Decimal('-Inf')):
            self.raise_error('invalid')

        return self.quantize(self.validate_precision(data))

    async def internal_to_external(self, data: Any) -> Any:
        if not isinstance(data, decimal.Decimal):
            data = decimal.Decimal(str(data).strip())

        quantized = self.quantize(data)

        if not self.coerce_to_string:
            return quantized
        return ('{:%sf}' % self.decimal_places).format(quantized)

    def validate_precision(self, value):
        """
        Ensure the number does not exceed max_digits and decimal_places.
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
        Quantize the decimal value to the configured precision.
        """
        if self.decimal_places is None:
            return value

        context = decimal.getcontext().copy()
        if self.max_digits is not None:
            context.prec = self.max_digits
        return value.quantize(decimal.Decimal('.1') ** self.decimal_places, rounding=self.rounding, context=context)

    def to_openapi(self) -> Schema:
        keywords = self._default_clsattr_to_oapiattr()
        if self.max_value is not None:
            keywords['maximum'] = self.max_value
        if self.min_value is not None:
            keywords['minimum'] = self.min_value
        if self.MAX_STRING_LENGTH is not None:
            keywords['maxLength'] = self.MAX_STRING_LENGTH

        return Float(**keywords)


class BooleanField(Field):
    """
    Boolean field for handling boolean data.

    Attributes:
        TRUE_VALUES (set): Set of values interpreted as True.
        FALSE_VALUES (set): Set of values interpreted as False.
        NULL_VALUES (set): Set of values interpreted as Null.
        default_error_messages (dict): Custom error messages for validation.
    """

    default_error_messages = {
        'invalid': 'Must be a valid boolean.',
    }
    TRUE_VALUES = {'t', 'T', 'y', 'Y', 'yes', 'YES', 'true', 'True', 'TRUE', 'on', 'On', 'ON', '1', 1, True}
    FALSE_VALUES = {'f', 'F', 'n', 'N', 'no', 'NO', 'false', 'False', 'FALSE', 'off', 'Off', 'OFF', '0', 0, 0.0, False}
    NULL_VALUES = {'null', 'Null', 'NULL', '', None}

    async def external_to_internal(self, data: Any) -> Any:
        try:
            if data in self.TRUE_VALUES:
                return True
            elif data in self.FALSE_VALUES:
                return False
            elif data in self.NULL_VALUES and self.allow_null:
                return None
            self.raise_error('invalid')
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

    def to_openapi(self) -> Schema:
        keywords = self._default_clsattr_to_oapiattr()
        return Boolean(**keywords)


class DateTimeField(Field):
    """
    DateTime field for handling datetime data.

    Attributes:
        output_format (str): Format for output datetime string.
        input_format (str): Format for input datetime string.
        set_timezone (timezone): Timezone to set for the datetime.
        default_error_messages (dict): Custom error messages for validation.
    """

    default_error_messages = {
        'invalid': 'Wrong type, should be datetime or string',
        'format': 'Datetime has wrong format. Use one of these formats instead: {format}.',
        'overflow': 'Datetime value out of range.',
    }

    def __init__(
        self, output_format='%Y-%m-%d %H:%M:%S', input_format='%Y-%m-%d %H:%M:%S', set_timezone: timezone = None, *args, **kwargs
    ):
        """
        Initialize DateTimeField with optional output_format, input_format, and set_timezone.

        Args:
            output_format (str, optional): Format for output datetime string. Defaults to '%Y-%m-%d %H:%M:%S'.
            input_format (str, optional): Format for input datetime string. Defaults to '%Y-%m-%d %H:%M:%S'.
            set_timezone (timezone, optional): Timezone to set for the datetime. Defaults to None.
        """
        self.output_format = output_format
        self.input_format = input_format
        if set_timezone is not None:
            self.set_timezone = set_timezone
        else:
            self.set_timezone = self.get_default_timezone()
        super(DateTimeField, self).__init__(*args, **kwargs)

    def get_default_timezone(self):
        """Set the default timezone to Beijing Time."""
        # TODO: Timezone setting should be configured in the settings file.
        return TIMEZONE

    def enforce_timezone(self, value):
        """Enforce a specific timezone."""
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
        return data.strftime(self.output_format)

    def to_openapi(self) -> Schema:
        keywords = self._default_clsattr_to_oapiattr()

        return DateTime(**keywords)


class DateField(Field):
    """
    Date field for handling date data.

    Attributes:
        output_format (str): Format for output date string.
        input_format (str): Format for input date string.
        default_error_messages (dict): Custom error messages for validation.
    """

    default_error_messages = {
        'invalid': 'Wrong type, should be date or string',
        'format': 'Datetime has wrong format. Use one of these formats instead: {format}.',
    }

    def __init__(self, output_format='%Y-%m-%d', input_format='%Y-%m-%d', *args, **kwargs):
        """
        Initialize DateField with optional output_format and input_format.

        Args:
            output_format (str, optional): Format for output date string. Defaults to '%Y-%m-%d'.
            input_format (str, optional): Format for input date string. Defaults to '%Y-%m-%d'.
        """
        self.output_format = output_format
        self.input_format = input_format
        super(DateField, self).__init__(*args, **kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        if not data:
            return None
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
        return data.strftime(self.output_format)

    def to_openapi(self) -> Schema:
        keywords = self._default_clsattr_to_oapiattr()

        return Date(**keywords)


class TimeField(Field):
    """
    Time field for handling time data.

    Attributes:
        output_format (str): Format for output time string.
        input_format (str): Format for input time string.
        default_error_messages (dict): Custom error messages for validation.
    """

    _documentation_type = 'string'
    _documentation_format = 'time'

    default_error_messages = {
        'invalid': 'Wrong type, should be datetime.time',
        'format': 'Time has wrong format. Use one of these formats instead: {format}.',
    }

    def __init__(self, output_format='%H:%M:%S', input_format='%H:%M:%S', *args, **kwargs):
        """
        Initialize TimeField with optional output_format and input_format.

        Args:
            output_format (str, optional): Format for output time string. Defaults to '%H:%M:%S'.
            input_format (str, optional): Format for input time string. Defaults to '%H:%M:%S'.
        """
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
        return data.strftime(self.output_format)

    def to_openapi(self) -> Schema:
        keywords = self._default_clsattr_to_oapiattr()

        return Time(**keywords)


class ChoiceField(Field):
    """
    Field for handling choices.

    Attributes:
        choices (list): List of valid choices.
        default_error_messages (dict): Custom error messages for validation.
    """

    default_error_messages = {
        'invalid_choice': '"{input}" is not a valid choice.',
    }

    def __init__(self, choices, *args, **kwargs):
        """
        Initialize ChoiceField with choices.

        Args:
            choices (list): List of valid choices in the form of (key, value) tuples.
        """
        self.choices = choices
        super(ChoiceField, self).__init__(*args, **kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        if self.check_key_choices(data):
            return self.choices_get_value_by_key(data)
        self.raise_error('invalid_choice', input=data)

    async def internal_to_external(self, data: Any) -> Any:
        choices_dict = {value: key for key, value in self.choices}
        if data not in choices_dict:
            return data
        return choices_dict.get(data, data)

    def choices_get_value_by_key(self, key):
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

    def to_openapi(self) -> Schema:
        keywords = self._default_clsattr_to_oapiattr()
        keywords['enum'] = [key for key, _ in self.choices]
        return String(**keywords)


class EnumChoiceField(Field):
    """
    Field for handling enum choices.

    Attributes:
        enum_type (type): The enum type.
        value_type (type): The value type.
        NULL_VALUES (set): Set of values interpreted as Null.
        default_error_messages (dict): Custom error messages for validation.
    """

    NULL_VALUES = {'', None}
    default_error_messages = {
        'invalid_choice': '"{input}" is not a valid choice.',
    }

    def __init__(self, enum_type, value_type, *args, **kwargs):
        """
        Initialize EnumChoiceField with enum_type and value_type.

        Args:
            enum_type (type): The enum type.
            value_type (type): The value type.
        """
        self.enum_type = enum_type
        self.value_type = value_type
        super(EnumChoiceField, self).__init__(*args, **kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        if data in self.NULL_VALUES and self.allow_null:
            return None
        if isinstance(data, self.enum_type):
            return data
        try:
            return self.enum_type(self.value_type(data)) if data is not None else None
        except ValueError:
            self.raise_error('invalid_choice', input=data)

    async def internal_to_external(self, data: Any) -> Any:
        if isinstance(data, Enum):
            return self.value_type(data.value)
        if isinstance(data, self.value_type):
            return self.value_type(self.enum_type(data).value)
        return self.value_type(data)

    def to_openapi(self) -> Schema:
        keywords = self._default_clsattr_to_oapiattr()
        keywords['enum'] = [e.value for e in self.enum_type]

        return Schema.make(self.value_type, **keywords)


class ListField(Field):
    """
    Field for handling a list of items.

    Attributes:
        child (Field): The field type for the items in the list.
        initial (list): The initial value of the list.
        allow_empty (bool): Whether to allow empty lists.
        max_length (int): Maximum number of items allowed in the list.
        min_length (int): Minimum number of items required in the list.
        default_error_messages (dict): Custom error messages for validation.
    """

    child = None
    initial = []
    default_error_messages = {
        'not_a_list': 'Expected a list of items but got type "{input_type}".',
        'empty': 'This list may not be empty.',
        'min_length': 'Ensure this field has at least {min_length} elements.',
        'max_length': 'Ensure this field has no more than {max_length} elements.',
    }

    def __init__(self, **kwargs):
        """
        Initialize ListField with optional child field, allow_empty, max_length, and min_length.

        Args:
            child (Field, optional): The field type for the items in the list.
            allow_empty (bool, optional): Whether to allow empty lists. Defaults to True.
            max_length (int, optional): Maximum number of items allowed in the list. Defaults to None.
            min_length (int, optional): Minimum number of items required in the list. Defaults to None.
        """
        self.child = kwargs.pop('child', copy.deepcopy(self.child))
        self.allow_empty = kwargs.pop('allow_empty', True)
        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)

        assert not inspect.isclass(self.child), '`child` has not been instantiated.'
        assert self.child.source is None, (
            "The `source` argument is not meaningful when applied to a `child=` field. " "Remove `source=` from the field declaration."
        )

        super().__init__(**kwargs)
        self.child.bind(field_name='', parent=self)
        if self.max_length is not None:
            message = {'max_length': 'Ensure this field has no more than {max_length} elements.'}
            self.validators.append(MaxLengthValidator(self.max_length, message=message))
        if self.min_length is not None:
            message = {'min_length': 'Ensure this field has at least {min_length} elements.'}
            self.validators.append(MinLengthValidator(self.min_length, message=message))

    async def external_to_internal(self, data: Any) -> Any:
        if isinstance(data, (str, Mapping)) or not hasattr(data, '__iter__'):
            self.raise_error('not_a_list', input_type=type(data).__name__)
        if not self.allow_empty and len(data) == 0:
            self.raise_error('empty')
        return await self.run_child_validation(data)

    async def internal_to_external(self, data: Any) -> Any:
        return [await self.child.internal_to_external(item) if item is not None else None for item in data]

    async def run_child_validation(self, data):
        """
        Validate each item in the list.
        """
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

    def to_openapi(self) -> Schema:
        keywords = self._default_clsattr_to_oapiattr()
        keywords['items'] = self.child.to_openapi()
        if self.max_length is not None:
            keywords['maxItems'] = self.max_length
        if self.min_length is not None:
            keywords['minItems'] = self.min_length
        return Array(**keywords)


# ##########
# below is for tortoise ORM related fields
# ##########
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
        except (TypeError, ValueError) as exc:
            logger.error(exc)
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


# TODO: 在 openapi 2.0 文档的返回值上需要进行优化
class ManyRelatedField(RelatedField):
    default_error_messages = {
        'invalid': 'Invalid value.',
        'not_exist': 'This value `{value}` is not valid',
    }

    def __init__(self, child_relation, **kwargs):
        self.child_relation = child_relation
        super(ManyRelatedField, self).__init__(**kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        return [await self.child_relation.external_to_internal(item) for item in data]

    async def internal_to_external(self, data: Any) -> Any:
        return [await self.child_relation.internal_to_external(value) for value in data]

    def _doc_properties(self):
        return {"title": '状态码', "type": 'array', "items": self.child_relation._doc_properties()}


# TODO: 在 openapi 2.0 文档的返回值上需要进行优化
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

    def to_openapi(self) -> Schema:
        return String()

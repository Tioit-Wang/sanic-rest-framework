import pytest

from rest_framework.exceptions import ValidationException
from rest_framework.validators import MaxLengthValidator, MinLengthValidator, MaxValueValidator, MinValueValidator, ValidatorAssertError


# MaxLengthValidator 测试


def test_max_length_validator():
    validator = MaxLengthValidator(5)
    # 有效值
    validator("test")  # 长度为4的字符串
    validator([1, 2, 3])  # 长度为3的列表
    # 无效值
    with pytest.raises(ValidationException):
        validator("too_long")  # 长度为7的字符串
    with pytest.raises(ValidatorAssertError):
        MaxLengthValidator("invalid")  # 非数值类型的 max_length 参数


# MinLengthValidator 测试


def test_min_length_validator():
    validator = MinLengthValidator(3)
    # 有效值
    validator("test")  # 长度为4的字符串
    validator([1, 2, 3, 4])  # 长度为4的列表
    # 无效值
    with pytest.raises(ValidationException):
        validator("hi")  # 长度为2的字符串
    with pytest.raises(ValidatorAssertError):
        MinLengthValidator("invalid")  # 非数值类型的 min_length 参数


# MaxValueValidator 测试


def test_max_value_validator():
    validator = MaxValueValidator(10)
    # 有效值
    validator(5)  # 小于最大值的整数
    validator(10)  # 等于最大值的整数
    # 无效值
    with pytest.raises(ValidationException):
        validator(15)  # 大于最大值的整数
    with pytest.raises(ValidatorAssertError):
        MaxValueValidator("invalid")  # 非数值类型的 max_value 参数


# MinValueValidator 测试


def test_min_value_validator():
    validator = MinValueValidator(5)
    # 有效值
    validator(10)  # 大于最小值的整数
    validator(5)  # 等于最小值的整数
    # 无效值
    with pytest.raises(ValidationException):
        validator(3)  # 小于最小值的整数
    with pytest.raises(ValidatorAssertError):
        MinValueValidator("invalid")  # 非数值类型的 min_value 参数

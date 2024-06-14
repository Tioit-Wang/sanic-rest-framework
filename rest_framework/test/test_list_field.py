import datetime
import decimal
from enum import Enum
import unittest

from rest_framework.exceptions import ValidationException
from rest_framework.fields import (
    ListField,
    CharField,
    IntegerField,
    FloatField,
    DecimalField,
    BooleanField,
    DateTimeField,
    DateField,
    TimeField,
    ChoiceField,
    EnumChoiceField,
)


class TestEnum(Enum):
    choice1 = 1
    choice2 = 2


class TestListField(unittest.IsolatedAsyncioTestCase):
    async def test_char_list_field(self):
        child_field = CharField(allow_null=True, max_length=5, min_length=1)
        field = ListField(child=child_field)

        # 验证 入参与出参
        valid_data = ['a', 'bc', 'def']
        invalid_data = [None, '']
        self.assertEqual(await field.run_validation(valid_data), valid_data)
        with self.assertRaises(ValidationException):
            await field.run_validation(invalid_data)

        # 验证 openapi结果
        expected_openapi = {
            'type': 'array',
            'items': {'type': 'string', 'nullable': True, 'required': True, 'maxLength': 5, 'minLength': 1},
            'nullable': False,
            'required': True,
        }
        self.assertEqual(field.to_openapi().serialize(), expected_openapi)

    async def test_int_list_field(self):
        child_field = IntegerField(allow_null=True, max_value=3, min_value=1)
        field = ListField(child=child_field)

        # 验证 入参与出参
        valid_data = [1, 2, 3]
        invalid_data = ['a', None]
        self.assertEqual(await field.run_validation(valid_data), valid_data)
        with self.assertRaises(ValidationException):
            await field.run_validation(invalid_data)

        # 验证 openapi结果
        expected_openapi = {
            'type': 'array',
            'items': {'type': 'integer', 'format': 'int32', 'nullable': True, 'required': True, 'maximum': 3, 'minimum': 1},
            'nullable': False,
            'required': True,
        }
        self.assertEqual(field.to_openapi().serialize(), expected_openapi)

    async def test_float_list_field(self):
        child_field = FloatField(allow_null=True)
        field = ListField(child=child_field)

        # 验证 入参与出参
        valid_data = [1.1, 2.2, 3.3]
        invalid_data = ['a', None]
        self.assertEqual(await field.run_validation(valid_data), valid_data)
        with self.assertRaises(ValidationException):
            await field.run_validation(invalid_data)

        # 验证 openapi结果
        expected_openapi = {
            'type': 'array',
            'items': {'type': 'number', 'format': 'float', 'nullable': True, 'required': True},
            'nullable': False,
            'required': True,
        }
        self.assertEqual(field.to_openapi().serialize(), expected_openapi)

    async def test_decimal_list_field(self):
        child_field = DecimalField(allow_null=True, max_value=4, min_value=1, max_digits=10, decimal_places=2)
        field = ListField(child=child_field)

        # 验证 入参与出参
        valid_data = [1.1, 2.2, 3.3]
        invalid_data = ['a', None]
        self.assertEqual(
            await field.run_validation(valid_data), [decimal.Decimal("1.10"), decimal.Decimal("2.20"), decimal.Decimal("3.30")]
        )
        with self.assertRaises(ValidationException):
            await field.run_validation(invalid_data)

        # 验证 openapi结果
        expected_openapi = {
            'type': 'array',
            'items': {
                'type': 'number',
                'format': 'float',
                'nullable': True,
                'required': True,
                'maximum': 4,
                'minimum': 1,
                'maxLength': 1000,
            },
            'nullable': False,
            'required': True,
        }
        self.assertEqual(field.to_openapi().serialize(), expected_openapi)

    async def test_boolean_list_field(self):
        child_field = BooleanField(allow_null=True)
        field = ListField(child=child_field)

        # 验证 入参与出参
        valid_data = [True, False, True]
        invalid_data = ['a', None]
        self.assertEqual(await field.run_validation(valid_data), valid_data)
        with self.assertRaises(ValidationException):
            await field.run_validation(invalid_data)

        # 验证 openapi结果
        expected_openapi = {
            'type': 'array',
            'items': {'type': 'boolean', 'nullable': True, 'required': True},
            'nullable': False,
            'required': True,
        }
        self.assertEqual(field.to_openapi().serialize(), expected_openapi)

    async def test_datetime_list_field(self):
        child_field = DateTimeField(allow_null=True, input_format="%Y-%m-%dT%H:%M:%S%z", output_format="%Y-%m-%dT%H:%M:%S%z")
        field = ListField(child=child_field)

        # 验证 入参与出参
        valid_data = ['2023-01-01T00:00:00Z', '2023-01-02T00:00:00Z']
        invalid_data = ['a', None]
        self.assertEqual(
            await field.run_validation(valid_data),
            [
                datetime.datetime(2023, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
                datetime.datetime(2023, 1, 2, 0, 0, 0, tzinfo=datetime.timezone.utc),
            ],
        )
        with self.assertRaises(ValidationException):
            await field.run_validation(invalid_data)

        # 验证 openapi结果
        expected_openapi = {
            'type': 'array',
            'items': {'type': 'string', 'format': 'date-time', 'nullable': True, 'required': True},
            'nullable': False,
            'required': True,
        }
        self.assertEqual(field.to_openapi().serialize(), expected_openapi)

    async def test_date_list_field(self):
        child_field = DateField(allow_null=True)
        field = ListField(child=child_field)

        # 验证 入参与出参
        valid_data = ['2023-01-01', '2023-01-02']
        invalid_data = ['a', None]
        self.assertEqual(
            await field.run_validation(valid_data),
            [
                datetime.date(2023, 1, 1),
                datetime.date(2023, 1, 2),
            ],
        )
        with self.assertRaises(ValidationException):
            await field.run_validation(invalid_data)

        # 验证 openapi结果
        expected_openapi = {
            'type': 'array',
            'items': {'type': 'string', 'format': 'date', 'nullable': True, 'required': True},
            'nullable': False,
            'required': True,
        }
        self.assertEqual(field.to_openapi().serialize(), expected_openapi)

    async def test_time_list_field(self):
        child_field = TimeField(allow_null=True)
        field = ListField(child=child_field)

        # 验证 入参与出参
        valid_data = ['00:00:00', '12:00:00']
        invalid_data = ['a', None]
        self.assertEqual(await field.run_validation(valid_data), [datetime.time(0, 0, 0), datetime.time(12, 0, 0)])
        with self.assertRaises(ValidationException):
            await field.run_validation(invalid_data)

        # 验证 openapi结果
        expected_openapi = {
            'type': 'array',
            'items': {'type': 'string', 'format': 'time', 'nullable': True, 'required': True},
            'nullable': False,
            'required': True,
        }
        self.assertEqual(field.to_openapi().serialize(), expected_openapi)

    async def test_choice_list_field(self):
        child_field = ChoiceField(choices=(('choice1', '1'), ('choice2', '2')), allow_null=True)
        field = ListField(child=child_field)

        # 验证 入参与出参
        valid_data = ['choice1', 'choice2']
        invalid_data = ['a', None]
        self.assertEqual(await field.run_validation(valid_data), ['1', '2'])
        with self.assertRaises(ValidationException):
            await field.run_validation(invalid_data)

        # 验证 openapi结果
        expected_openapi = {
            'type': 'array',
            'items': {'type': 'string', 'nullable': True, 'required': True, 'enum': ['choice1', 'choice2']},
            'nullable': False,
            'required': True,
        }
        self.assertEqual(field.to_openapi().serialize(), expected_openapi)

    async def test_enum_choice_list_field(self):

        child_field = EnumChoiceField(enum_type=TestEnum, value_type=int, allow_null=True)
        field = ListField(child=child_field)

        # 验证 入参与出参
        valid_data = [1, 2]
        invalid_data = ['a', None]
        self.assertEqual(await field.run_validation(valid_data), [TestEnum.choice1, TestEnum.choice2])
        with self.assertRaises(ValidationException):
            await field.run_validation(invalid_data)

        # 验证 openapi结果
        expected_openapi = {
            'type': 'array',
            'items': {'type': 'integer', 'format': 'int32', 'nullable': True, 'required': True, 'enum': [1, 2]},
            'nullable': False,
            'required': True,
        }
        self.assertEqual(field.to_openapi().serialize(), expected_openapi)


if __name__ == '__main__':
    unittest.main()

import unittest
import re

from rest_framework.exceptions import ValidationException
from rest_framework.fields import IntegerField


class TestIntegerField(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.field = IntegerField(max_value=100, min_value=0)

    async def test_initialization(self):
        # Test that the field is initialized with the correct attributes
        self.assertEqual(self.field.max_value, 100)
        self.assertEqual(self.field.min_value, 0)
        self.assertEqual(self.field.MAX_STRING_LENGTH, 1000)
        self.assertTrue(isinstance(self.field.re_decimal, re.Pattern))

    async def test_external_to_internal_valid_int(self):
        # Test valid integer input
        data = 123
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, 123)

    async def test_external_to_internal_valid_string(self):
        # Test valid string input
        data = "123"
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, 123)

    async def test_external_to_internal_valid_decimal_string(self):
        # Test valid decimal string input
        data = "123.0"
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, 123)

    async def test_external_to_internal_invalid_type(self):
        # Test invalid input type
        data = "invalid_int"
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_external_to_internal_string_length_exceeded(self):
        # Test string input exceeding max length
        data = "1" * 1001
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_internal_to_external(self):
        # Test internal to external conversion
        data = 123
        result = await self.field.internal_to_external(data)
        self.assertEqual(result, 123)

    async def test_max_value_validator(self):
        # Test max value validation
        data = 200
        with self.assertRaises(ValidationException):
            await self.field.run_validation(data)

    async def test_min_value_validator(self):
        # Test min value validation
        data = -10
        with self.assertRaises(ValidationException):
            await self.field.run_validation(data)

    async def test_to_openapi(self):
        # Test OpenAPI schema generation
        expected_schema = {'type': 'integer', 'format': 'int32', 'nullable': False, 'required': True, 'maximum': 100, 'minimum': 0}
        self.assertEqual(self.field.to_openapi().serialize(), expected_schema)

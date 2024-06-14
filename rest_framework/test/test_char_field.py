import unittest

from rest_framework.exceptions import ValidationException
from rest_framework.fields import CharField


class TestCharField(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.field = CharField(max_length=10, min_length=3, trim_whitespace=True)

    async def test_initialization(self):
        # Test that the field is initialized with the correct attributes
        self.assertEqual(self.field.max_length, 10)
        self.assertEqual(self.field.min_length, 3)
        self.assertTrue(self.field.trim_whitespace)

    async def test_external_to_internal_valid_string(self):
        # Test valid string input
        data = "  valid  "
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, "valid")

    async def test_external_to_internal_valid_int(self):
        # Test valid integer input
        data = 123
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, "123")

    async def test_external_to_internal_valid_float(self):
        # Test valid float input
        data = 123.45
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, "123.45")

    async def test_external_to_internal_invalid_type(self):
        # Test invalid input type
        data = []
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_internal_to_external(self):
        # Test internal to external conversion
        data = 123
        result = await self.field.internal_to_external(data)
        self.assertEqual(result, "123")

    async def test_max_length_validator(self):
        # Test max length validation
        data = "toolongstring"
        with self.assertRaises(ValidationException):
            await self.field.run_validation(data)

    async def test_min_length_validator(self):
        # Test min length validation
        data = "no"
        with self.assertRaises(ValidationException):
            await self.field.run_validation(data)

    async def test_to_openapi(self):
        # Test OpenAPI schema generation
        expected_schema = {'type': 'string', 'nullable': False, 'required': True, 'maxLength': 10, 'minLength': 3}
        self.assertEqual(self.field.to_openapi().serialize(), expected_schema)

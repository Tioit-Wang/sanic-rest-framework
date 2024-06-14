import unittest

from rest_framework.exceptions import ValidationException
from rest_framework.fields import FloatField


class TestFloatField(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.field = FloatField(max_value=100.0, min_value=0.0)

    async def test_initialization(self):
        # Test that the field is initialized with the correct attributes
        self.assertEqual(self.field.max_value, 100.0)
        self.assertEqual(self.field.min_value, 0.0)

    async def test_external_to_internal_valid_float(self):
        # Test valid float input
        data = 123.45
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, 123.45)

    async def test_external_to_internal_valid_string(self):
        # Test valid string input
        data = "123.45"
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, 123.45)

    async def test_external_to_internal_invalid_type(self):
        # Test invalid input type
        data = "invalid_float"
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_external_to_internal_string_length_exceeded(self):
        # Test string input exceeding max length
        data = "1" * 1001
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_internal_to_external(self):
        # Test internal to external conversion
        data = 123.45
        result = await self.field.internal_to_external(data)
        self.assertEqual(result, 123.45)

    async def test_max_value_validator(self):
        # Test max value validation
        data = 200.0
        with self.assertRaises(ValidationException):
            await self.field.run_validation(data)

    async def test_min_value_validator(self):
        # Test min value validation
        data = -10.0
        with self.assertRaises(ValidationException):
            await self.field.run_validation(data)

    async def test_to_openapi(self):
        # Test OpenAPI schema generation
        expected_schema = {'type': 'number', 'format': 'float', 'nullable': False, 'required': True, 'maximum': 100.0, 'minimum': 0.0}
        self.assertEqual(self.field.to_openapi().serialize(), expected_schema)


if __name__ == "__main__":
    unittest.main()

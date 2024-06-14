import unittest
import asyncio
import datetime
from unittest.mock import MagicMock

from rest_framework.exceptions import ValidationException
from rest_framework.fields import TimeField


class TestTimeField(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.field = TimeField(output_format='%H:%M:%S', input_format='%H:%M:%S')

    async def test_initialization(self):
        # Test that the field is initialized with the correct attributes
        self.assertEqual(self.field.output_format, '%H:%M:%S')
        self.assertEqual(self.field.input_format, '%H:%M:%S')

    async def test_external_to_internal_valid_string(self):
        # Test valid string input
        data = "15:30:45"
        result = await self.field.external_to_internal(data)
        expected = datetime.time(15, 30, 45)
        self.assertEqual(result, expected)

    async def test_external_to_internal_valid_time(self):
        # Test valid time input
        data = datetime.time(15, 30, 45)
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, data)

    async def test_external_to_internal_invalid_type(self):
        # Test invalid input type
        data = 12345
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_external_to_internal_invalid_format(self):
        # Test invalid string format
        data = "15-30-45"
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_internal_to_external(self):
        # Test internal to external conversion
        data = datetime.time(15, 30, 45)
        result = await self.field.internal_to_external(data)
        self.assertEqual(result, "15:30:45")

    async def test_internal_to_external_none(self):
        # Test conversion of None value
        data = None
        result = await self.field.internal_to_external(data)
        self.assertIsNone(result)

    async def test_internal_to_external_string(self):
        # Test conversion of string value
        data = "15:30:45"
        result = await self.field.internal_to_external(data)
        self.assertEqual(result, data)

    async def test_to_openapi(self):
        # Test OpenAPI schema generation
        expected_schema = {'type': 'string', 'format': 'time', 'nullable': False, 'required': True}
        self.assertEqual(self.field.to_openapi().serialize(), expected_schema)


if __name__ == "__main__":
    unittest.main()

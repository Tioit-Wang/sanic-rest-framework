import unittest
import datetime

from rest_framework.exceptions import ValidationException
from rest_framework.fields import DateField


class TestDateField(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.field = DateField(output_format='%Y-%m-%d', input_format='%Y-%m-%d')

    async def test_initialization(self):
        # Test that the field is initialized with the correct attributes
        self.assertEqual(self.field.output_format, '%Y-%m-%d')
        self.assertEqual(self.field.input_format, '%Y-%m-%d')

    async def test_external_to_internal_valid_string(self):
        # Test valid string input
        data = "2024-06-04"
        result = await self.field.external_to_internal(data)
        expected = datetime.date(2024, 6, 4)
        self.assertEqual(result, expected)

    async def test_external_to_internal_valid_date(self):
        # Test valid date input
        data = datetime.date(2024, 6, 4)
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, data)

    async def test_external_to_internal_invalid_type(self):
        # Test invalid input type
        data = 12345
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_external_to_internal_invalid_format(self):
        # Test invalid string format
        data = "2024/06/04"
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_internal_to_external(self):
        # Test internal to external conversion
        data = datetime.date(2024, 6, 4)
        result = await self.field.internal_to_external(data)
        self.assertEqual(result, "2024-06-04")

    async def test_internal_to_external_none(self):
        # Test conversion of None value
        data = None
        result = await self.field.internal_to_external(data)
        self.assertIsNone(result)

    async def test_internal_to_external_string(self):
        # Test conversion of string value
        data = "2024-06-04"
        result = await self.field.internal_to_external(data)
        self.assertEqual(result, data)

    async def test_to_openapi(self):
        # Test OpenAPI schema generation
        expected_schema = {'type': 'string', 'format': 'date', 'nullable': False, 'required': True}
        self.assertEqual(self.field.to_openapi().serialize(), expected_schema)


if __name__ == "__main__":
    unittest.main()
